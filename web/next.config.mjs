/** @type {import('next').NextConfig} */
const nextConfig = {
  // transformers.js + onnxruntime-node chạy ở server (Node runtime), không bundle qua webpack
  serverExternalPackages: ["@huggingface/transformers", "onnxruntime-node", "sharp"],

  // Đưa file index (embedding đã tính sẵn) vào gói serverless function khi deploy Vercel
  outputFileTracingIncludes: {
    "/api/**": ["./data/index/**"],
  },

  // Bỏ binary onnxruntime của các nền tảng khác Linux x64 để gói function < 250MB trên Vercel
  outputFileTracingExcludes: {
    "/api/**": [
      "./node_modules/onnxruntime-node/bin/napi-v3/darwin/**",
      "./node_modules/onnxruntime-node/bin/napi-v3/win32/**",
      "./node_modules/onnxruntime-node/bin/napi-v3/linux/arm64/**",
      "./node_modules/@img/sharp-libvips-darwin*/**",
      "./node_modules/@img/sharp-win32*/**",
      "./.cache/**",
    ],
  },
};

export default nextConfig;
