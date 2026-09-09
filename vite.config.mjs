import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({ root: resolve("src/ui/frontend"), base: "/static/app/", build: { outDir: resolve("src/ui/static/app"), emptyOutDir: true } });
