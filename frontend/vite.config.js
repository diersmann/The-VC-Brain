import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
export default defineConfig(function (_a) {
    var _b;
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    return {
        plugins: [react()],
        resolve: {
            alias: {
                "react-native": "react-native-web",
            },
            extensions: [".web.tsx", ".web.ts", ".tsx", ".ts", ".jsx", ".js"],
        },
        server: {
            port: 5173,
            proxy: {
                "/api": (_b = env.VITE_API_PROXY_TARGET) !== null && _b !== void 0 ? _b : "http://localhost:8000",
            },
        },
        test: {
            environment: "jsdom",
            setupFiles: "./src/test/setup.ts",
        },
    };
});
