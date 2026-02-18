import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 프로덕션 빌드 시 독립 실행형 출력 (Docker/VPS 배포용)
  output: "standalone",

  // 프로덕션 소스맵 비활성화 (보안 + 번들 크기)
  productionBrowserSourceMaps: false,

  // 이미지 최적화 — 외부 이미지 사용 시 도메인 허용
  images: {
    unoptimized: true,
  },

  // 서버 외부 패키지 (Python 프록시에서 사용하는 서버 전용 모듈)
  serverExternalPackages: ["js-yaml", "yahoo-finance2"],
};

export default nextConfig;
