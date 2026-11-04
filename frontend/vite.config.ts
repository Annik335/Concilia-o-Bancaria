<<<<<<< HEAD
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';
  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: { '/api': { target, changeOrigin: true } },
    },
  };
});
=======
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins:[react()], server:{port:5173,host:'0.0.0.0'} });
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
