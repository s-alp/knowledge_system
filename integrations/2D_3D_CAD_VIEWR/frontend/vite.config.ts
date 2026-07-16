import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const DEV_PROXY_TARGET = process.env.VITE_DEV_PROXY_TARGET ?? "http://127.0.0.1:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: DEV_PROXY_TARGET,
        changeOrigin: false,
      },
      "/drawing-metadata": {
        target: DEV_PROXY_TARGET,
        changeOrigin: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
            return "react-vendor";
          }

          if (
            id.includes("node_modules/three") ||
            id.includes("node_modules/@react-three/fiber") ||
            id.includes("node_modules/@react-three/drei") ||
            id.includes("three/examples/jsm/loaders/")
          ) {
            return "viewer-3d-vendor";
          }

          if (id.includes("node_modules/pdfjs-dist") || id.includes("node_modules/utif")) {
            return "viewer-2d-vendor";
          }

          return undefined;
        },
      },
    },
  },
});
