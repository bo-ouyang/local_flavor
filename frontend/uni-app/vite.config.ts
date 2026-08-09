import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

const uniPlugin = typeof uni === 'function' ? uni : (uni as any).default;

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [uniPlugin()],
});
