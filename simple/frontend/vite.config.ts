import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Запросы к API идут на VITE_API_URL; на backend нужен CORS (см. simple/app/main.py).
  },
});
