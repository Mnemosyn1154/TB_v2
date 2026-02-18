# web/ — D2trader Next.js 프론트엔드

Next.js 16 + React 19 + TypeScript 5.9 + Tailwind CSS 4 + shadcn/ui

## 아키텍처

- App Router (`web/app/`)
- 6탭 SPA: Portfolio, Benchmark, Strategy, Backtest, Paper Trading, Control
- `page.tsx`에서 클라이언트 사이드 탭 전환
- 다크 모드 기본 (`ThemeProvider defaultTheme="dark"`)

## 디렉토리 구조

```
web/
├── app/
│   ├── api/               # API 프록시 라우트 (Next.js → Python API)
│   │   ├── backtest/      # /api/backtest/* → /py/backtest/*
│   │   ├── bot/           # /api/bot/* → /py/bot/*
│   │   ├── paper/         # /api/paper/* → /py/paper/*
│   │   ├── portfolio/     # /api/portfolio → /py/portfolio
│   │   ├── signals/       # /api/signals → /py/signals
│   │   ├── settings/      # /api/settings → settings.yaml 직접 읽기/쓰기
│   │   └── benchmark/     # /api/benchmark → Yahoo Finance 직접 호출
│   ├── page.tsx           # 메인 대시보드 (6탭)
│   ├── layout.tsx         # 루트 레이아웃 (ThemeProvider, Geist 폰트)
│   └── globals.css        # OKLCH 색상 토큰, Tailwind 설정
├── components/
│   ├── ui/                # shadcn/ui 프리미티브 (수정 금지)
│   ├── common/            # 공통 컴포넌트 (loading, error, metrics-card)
│   ├── layout/            # 페이지 레이아웃, 네비게이션
│   ├── portfolio/         # 포트폴리오 탭 컴포넌트
│   ├── benchmark/         # 벤치마크 탭 컴포넌트
│   ├── strategy/          # 전략 설정 탭 컴포넌트
│   ├── backtest/          # 백테스트 탭 컴포넌트
│   ├── paper/             # 페이퍼 트레이딩 탭 컴포넌트
│   └── control/           # 봇 제어 탭 컴포넌트
├── hooks/                 # 커스텀 React 훅
│   ├── use-api.ts         # 범용 API 훅: { data, error, loading, refetch }
│   ├── use-interval.ts    # setInterval 래퍼 (폴링용)
│   ├── use-portfolio.ts   # 포트폴리오 데이터 + 자동 폴링
│   ├── use-benchmark.ts   # 벤치마크 데이터 + 기간 선택
│   ├── use-backtest.ts    # 백테스트 실행 { run, result, clear }
│   ├── use-bot-status.ts  # 봇 상태 30초 폴링
│   └── use-control.ts     # 킬스위치, 봇 실행, 트레이딩 모드, 로그뷰어
├── lib/
│   ├── api-client.ts      # 모든 API 호출 함수 (캐시 포함)
│   ├── python-proxy.ts    # pythonGet/pythonPost (서버 사이드 프록시)
│   ├── formatters.ts      # 숫자/날짜 포매팅 유틸
│   └── constants.ts       # 상수 (폴링 주기, 차트 설정 등)
└── types/                 # TypeScript 타입 정의
    ├── common.ts          # ApiResponse<T>, Market, TradeSide
    ├── portfolio.ts       # Position, RiskSummary, PortfolioData
    ├── benchmark.ts       # BenchmarkMetrics, BenchmarkData
    ├── backtest.ts        # BacktestRequest, BacktestResult, Trade
    ├── paper.ts           # PaperSession, PaperSignal, PaperTrade
    ├── control.ts         # TradingMode, KillSwitchStatus, BotStatus, LogEntry
    └── strategy.ts        # StrategyConfig, StrategiesData
```

## API 프록시 패턴

대부분의 API 라우트는 Python API로 프록시:

```typescript
// web/app/api/portfolio/route.ts (예시)
import { pythonGet } from "@/lib/python-proxy";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const data = await pythonGet("/py/portfolio");
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ data: null, error: String(e) }, { status: 502 });
  }
}
```

예외:
- `/api/settings/*` → `config/settings.yaml` 직접 읽기/쓰기
- `/api/benchmark` → yahoo-finance2 패키지 직접 호출

## 컴포넌트 규칙

- 탭 컨테이너: `{domain}-tab.tsx` (예: `portfolio-tab.tsx`)
- 하위 컴포넌트: `{feature}.tsx` (예: `holdings-table.tsx`)
- `"use client"` 디렉티브: 인터랙티브 컴포넌트에 필수
- `components/ui/` 하위 파일은 shadcn/ui가 생성한 것이므로 직접 수정 금지

## 명령어

```bash
npm run dev    # 개발 서버 (port 3000)
npm run build  # 프로덕션 빌드 (standalone output)
npm run lint   # ESLint
```

## 환경변수

`web/.env.local`:
```
PYTHON_API_URL=http://localhost:8000
PYTHON_API_SECRET=your-secret-here
```
