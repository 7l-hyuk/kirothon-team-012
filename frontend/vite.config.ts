import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// 개발 서버의 /api 요청을 넘길 백엔드. 기본은 배포 서버(CloudFront)이고,
// 로컬 백엔드를 쓸 때는 frontend/.env.local 에 API_PROXY_TARGET=http://localhost:8000 을 넣는다.
// 배포 서버는 CORS를 열지 않으므로 브라우저가 직접 부르지 않고 이 프록시를 거친다.
const DEFAULT_TARGET = 'https://www.room2ate.cloud'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.API_PROXY_TARGET || DEFAULT_TARGET
  return {
    plugins: [react()],
    server: {
      proxy: { '/api': { target, changeOrigin: true } },
    },
  }
})
