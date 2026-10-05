import { defineConfig } from "vite";
export default defineConfig({
  base: process.env.VITE_STATIC_DEMO === "1" ? "/fieldops-agent/" : "/",
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/sandbox": "http://127.0.0.1:8765",
    },
  },
});
