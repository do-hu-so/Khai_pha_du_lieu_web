/**
 * Chuẩn hóa & token hóa tiếng Việt cho BM25.
 * Port 1-1 của pipeline/nlp/normalize.py - hai bên PHẢI cho kết quả giống nhau.
 */

const VI_CHARS = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ";
const LETTERS = "a-z" + VI_CHARS;
const TOKEN_RE = new RegExp(`[0-9${LETTERS}]+`, "g");

/** "hoà" -> "hòa", "thuỷ" -> "thủy" (chỉ khi ở cuối âm tiết, không sau "q") */
const VARIANT_TO_CANONICAL: Record<string, string> = {
  "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
  "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
  "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
};
const TONE_RE = new RegExp(
  `(?<!q)(${Object.keys(VARIANT_TO_CANONICAL).join("|")})(?![${LETTERS}])`,
  "g",
);

export function normalizeText(text: string): string {
  return text.normalize("NFC").replace(TONE_RE, (m) => VARIANT_TO_CANONICAL[m] ?? m);
}

/** Chữ Pāli/Sanskrit (Samaṇa, Saṅgha, Nibbāna) -> chữ Latin cơ bản để khớp cả cách viết không dấu */
const PALI_FROM = "āīūṅñṭḍṇḷṃṁḥśṣṛṝḹ";
const PALI_TO = "aiunntdnlmmhssrrl";
const PALI_RE = new RegExp(`[${PALI_FROM}]`, "g");

export function syllables(text: string): string[] {
  const s = normalizeText(text.toLowerCase()).replace(PALI_RE, (c) => PALI_TO[PALI_FROM.indexOf(c)]);
  return s.match(TOKEN_RE) ?? [];
}

/** Âm tiết + bigram âm tiết (bắt từ ghép: "vô_thường", "niết_bàn"). */
export function bm25Tokenize(text: string): string[] {
  const syl = syllables(text);
  const out = syl.slice();
  for (let i = 0; i + 1 < syl.length; i++) out.push(`${syl[i]}_${syl[i + 1]}`);
  return out;
}
