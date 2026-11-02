/**
 * Kiểm tra index trước khi deploy:  npm run check-index
 *  1. File index đầy đủ, kích thước ma trận khớp số chunk x số chiều, vector đã chuẩn hóa.
 *  2. Embedding bằng transformers.js (dùng ở web) KHỚP với embedding Python đã lưu:
 *     embed lại vài chunk ở Node rồi so cosine với vector trong index (kỳ vọng > 0.98).
 */
import fs from "node:fs";
import path from "node:path";

const dir = path.join(process.cwd(), "data", "index");
const manifest = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf-8"));
const chunks = JSON.parse(fs.readFileSync(path.join(dir, "chunks.json"), "utf-8"));
const buf = fs.readFileSync(path.join(dir, "embeddings.f32"));
const vectors = new Float32Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
const { dim } = manifest;

console.log(`Index: ${chunks.length} chunk, ${manifest.num_docs} văn bản, ${dim} chiều, mô hình ${manifest.model_name}`);
if (vectors.length !== chunks.length * dim) {
  console.error(`✗ Kích thước sai: ${vectors.length} != ${chunks.length} x ${dim}`);
  process.exit(1);
}
let badNorm = 0;
for (let i = 0; i < chunks.length; i++) {
  let s = 0;
  for (let j = 0; j < dim; j++) s += vectors[i * dim + j] ** 2;
  if (Math.abs(Math.sqrt(s) - 1) > 1e-3) badNorm++;
}
console.log(badNorm ? `✗ ${badNorm} vector chưa chuẩn hóa` : "✓ Mọi vector đã chuẩn hóa L2");

const { pipeline, env } = await import("@huggingface/transformers");
env.cacheDir = path.join(process.cwd(), ".cache");
const extractor = await pipeline("feature-extraction", manifest.web_model_name, { dtype: "q8" });
const sample = Array.from({ length: Math.min(5, chunks.length) }, (_, k) => Math.floor((k * chunks.length) / 5));
let min = 1;
for (const i of sample) {
  const c = chunks[i];
  const out = await extractor(`${manifest.passage_prefix}${c.title}\n${c.text}`, { pooling: "mean", normalize: true });
  let cos = 0;
  for (let j = 0; j < dim; j++) cos += out.data[j] * vectors[i * dim + j];
  min = Math.min(min, cos);
  console.log(`  chunk ${c.id.padEnd(28)} cosine(JS, Python) = ${cos.toFixed(4)}`);
}
console.log(min > 0.98 ? "✓ Embedding web khớp embedding Python" : "✗ Embedding lệch - kiểm tra web_model_name / prefix trong manifest");
process.exit(min > 0.98 && !badNorm ? 0 : 1);
