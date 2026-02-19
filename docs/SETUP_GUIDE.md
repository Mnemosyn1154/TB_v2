# SETUP_GUIDE.md — D2trader 개발 환경 셋업 가이드

> 코딩 초보자도 따라할 수 있는 단계별 개발 환경 구축 가이드.
> 기술 스택 상세는 [`WEB_PROJECT_SPEC.md`](./WEB_PROJECT_SPEC.md),
> 디자인 시스템은 [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md)를 참조합니다.

---

## 목차

1. [사전 준비물](#1-사전-준비물)
2. [프로젝트 구조 생성](#2-프로젝트-구조-생성)
3. [Next.js 프로젝트 초기화](#3-nextjs-프로젝트-초기화)
4. [shadcn/ui 설치 & 테마 설정](#4-shadcnui-설치--테마-설정)
5. [디자인 토큰 적용](#5-디자인-토큰-적용)
6. [핵심 라이브러리 설치](#6-핵심-라이브러리-설치)
7. [Python API 셋업](#7-python-api-셋업)
8. [환경변수 설정](#8-환경변수-설정)
9. [개발 서버 실행](#9-개발-서버-실행)
10. [Cloudflare 배포](#10-cloudflare-배포)
11. [트러블슈팅](#11-트러블슈팅)

---

## 1. 사전 준비물

### 1.1 필수 소프트웨어

| 소프트웨어 | 최소 버전 | 확인 명령어 | 설치 방법 |
|-----------|----------|------------|----------|
| **Node.js** | 18.17+ (LTS 권장) | `node -v` | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ (Node.js와 함께 설치) | `npm -v` | Node.js에 포함 |
| **Python** | 3.12+ (pyenv 3.12.12 권장) | `python3 --version` | [python.org](https://python.org/) 또는 pyenv |
| **pip** | 최신 | `pip3 --version` | Python에 포함 |
| **Git** | 2.30+ | `git --version` | [git-scm.com](https://git-scm.com/) |

### 1.2 선택 소프트웨어

| 소프트웨어 | 용도 | 설치 방법 |
|-----------|------|----------|
| **VS Code** | 코드 편집기 | [code.visualstudio.com](https://code.visualstudio.com/) |
| **cloudflared** | Cloudflare Tunnel (배포 시) | [설치 가이드](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |

### 1.3 VS Code 추천 확장

```
코드 편집:
  - ESLint (dbaeumer.vscode-eslint)
  - Prettier (esbenp.prettier-vscode)
  - Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)

Python:
  - Python (ms-python.python)

기타:
  - Error Lens (usernamehw.errorlens) — 에러를 코드 옆에 표시
```

### 1.4 Python 버전 관리 (pyenv)

프로젝트 루트에 `.python-version` 파일이 있어 pyenv 사용 시 자동으로 Python 3.12.12가 선택됩니다.

```bash
# pyenv 설치 (macOS)
brew install pyenv

# Python 3.12.12 설치
pyenv install 3.12.12

# 프로젝트 루트에서 자동 활성화 확인
cd TB_v2
python3 --version
# → Python 3.12.12
```

pyenv를 사용하지 않는 경우, 시스템 Python 3.12+ 이면 됩니다.

### 1.5 기존 프로젝트 확인

D2trader는 기존 AlgoTrader KR의 `src/`, `config/` 코드를 재활용한다.
셋업 전에 기존 프로젝트가 정상 동작하는지 확인:

```bash
# 기존 프로젝트 루트에서
python3 main.py status
# → 전략 상태가 출력되면 OK
```

---

## 2. 프로젝트 구조 생성

### 2.1 레포지토리 생성

**방법 A: 기존 레포에 추가** (권장 — 기존 src/ 코드를 직접 사용)

```bash
# 기존 AlgoTrader KR 레포 루트에서
mkdir -p web pyapi pyapi/routers
```

**방법 B: 새 레포 생성 후 기존 코드 복사**

```bash
mkdir D2trader && cd D2trader
git init

# 기존 프로젝트에서 필요한 디렉토리 복사
cp -r /path/to/AlgoTrader/src .
cp -r /path/to/AlgoTrader/config .
cp /path/to/AlgoTrader/main.py .
cp /path/to/AlgoTrader/requirements.txt .
cp /path/to/AlgoTrader/.env .

mkdir -p web pyapi pyapi/routers
```

### 2.2 최종 디렉토리 구조 확인

```
D2trader/
├── src/              ← 기존 (전략, 브로커, 엔진)
├── config/           ← 기존 (settings.yaml)
├── main.py           ← 기존 CLI
├── pyapi/            ← 신규 (Step 7에서 설정)
├── web/              ← 신규 (Step 3에서 생성)
├── data/             ← 기존 (DB, 토큰 캐시)
├── .env              ← 기존 + 추가 변수
└── requirements.txt  ← 기존 + fastapi, uvicorn
```

---

## 3. Next.js 프로젝트 초기화

### 3.1 프로젝트 생성

프로젝트 루트에서 실행:

```bash
npx create-next-app@latest web
```

프롬프트가 나오면 아래와 같이 선택:

```
✔ Would you like to use TypeScript?                  → Yes
✔ Would you like to use ESLint?                      → Yes
✔ Would you like to use Tailwind CSS?                → Yes
✔ Would you like your code inside a `src/` directory? → No
  (주의: No를 선택! — Python src/와 혼동 방지)
✔ Would you like to use App Router?                  → Yes
✔ Would you like to use Turbopack for next dev?      → Yes
✔ Would you like to customize the import alias?      → Yes → @/*
```

### 3.2 설치 확인

```bash
cd web
npm run dev
```

브라우저에서 `http://localhost:3000`을 열어 Next.js 기본 페이지가 보이면 성공.
`Ctrl+C`로 서버를 중단한다.

---

## 4. shadcn/ui 설치 & 테마 설정

### 4.1 shadcn/ui 초기화

`web/` 디렉토리에서:

```bash
npx shadcn@latest init
```

프롬프트 선택:

```
✔ Which style would you like to use?        → New York
✔ Which color would you like to use?        → Neutral
✔ Would you like to use CSS variables?      → Yes
```

### 4.2 필수 컴포넌트 설치

한 번에 설치:

```bash
npx shadcn@latest add card button table tabs badge dialog \
  dropdown-menu separator tooltip switch label input \
  select slider sheet scroll-area
```

설치 후 `web/components/ui/` 디렉토리에 파일들이 생성된다.

### 4.3 설치 확인

```
web/components/ui/
├── card.tsx
├── button.tsx
├── table.tsx
├── tabs.tsx
├── badge.tsx
├── dialog.tsx
├── dropdown-menu.tsx
├── separator.tsx
├── tooltip.tsx
├── switch.tsx
├── label.tsx
├── input.tsx
├── select.tsx
├── slider.tsx
├── sheet.tsx
└── scroll-area.tsx
```

---

## 5. 디자인 토큰 적용

### 5.1 globals.css 덮어쓰기

`web/app/globals.css`를 열고 내용을 아래로 교체한다.
(자세한 토큰 값은 `DESIGN_SYSTEM.md` 3.1절 참조)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* ── 기본 시맨틱 ── */
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 240 10% 14%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --success: 142 71% 45%;
    --success-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 240 10% 14%;
    --radius: 0.75rem;

    /* ── 시장별 색상 ── */
    --market-kr: 217 91% 60%;
    --market-us: 160 84% 39%;

    /* ── 차트 색상 ── */
    --chart-blue: #3b82f6;
    --chart-emerald: #10b981;
    --chart-purple: #a855f7;
    --chart-orange: #f59e0b;
    --chart-pink: #ec4899;
    --chart-teal: #14b8a6;
    --chart-red: #ef4444;
    --chart-gray: #6b7280;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --card: 0 0% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 0 0% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 10% 14%;
    --secondary: 0 0% 14.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 0 0% 14.9%;
    --muted-foreground: 0 0% 63.9%;
    --accent: 0 0% 14.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --success: 142 71% 35%;
    --success-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 14.9%;
    --ring: 0 0% 83.1%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

### 5.2 Geist 폰트 설정

`web/app/layout.tsx`를 열고 폰트를 Geist로 변경:

```typescript
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "D2trader",
  description: "AlgoTrader KR 대시보드",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className={`${GeistSans.variable} ${GeistMono.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

Geist 폰트 패키지 설치:

```bash
npm install geist
```

### 5.3 tailwind.config.ts 확장

`web/tailwind.config.ts`에 커스텀 색상 추가:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        market: {
          kr: "hsl(var(--market-kr))",
          us: "hsl(var(--market-us))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)"],
        mono: ["var(--font-geist-mono)"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

`tailwindcss-animate` 설치:

```bash
npm install tailwindcss-animate
```

---

## 6. 핵심 라이브러리 설치

`web/` 디렉토리에서:

```bash
# 차트
npm install recharts

# 다크/라이트 모드
npm install next-themes

# 아이콘
npm install lucide-react

# YAML 파싱 (전략 설정 읽기/쓰기)
npm install js-yaml
npm install -D @types/js-yaml

# 벤치마크 시세 조회
npm install yahoo-finance2
```

### 설치 확인

```bash
npm ls recharts next-themes lucide-react js-yaml yahoo-finance2
```

모든 패키지가 출력되면 OK.

---

## 7. Python API 셋업

### 7.1 Python 패키지 추가 설치

프로젝트 루트에서:

```bash
pip3 install fastapi uvicorn
```

기존 `requirements.txt`에도 추가:

```
# 기존 패키지들...
# D2trader Python API
fastapi>=0.104.0
uvicorn>=0.24.0
```

### 7.2 FastAPI 앱 생성

`pyapi/main.py` 생성:

```python
from __future__ import annotations

"""D2trader Python API — KIS/전략/백테스트 전용 경량 API"""

import sys
from pathlib import Path

# 프로젝트 루트를 import path에 추가 (기존 src/ 접근용)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="D2trader Python API", version="0.1.0")

# CORS — 개발 시 Next.js에서의 직접 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/py/health")
def health_check():
    """API 상태 확인용 (셋업 검증)"""
    return {"status": "ok", "message": "D2trader Python API is running"}
```

### 7.3 시크릿 검증 미들웨어

`pyapi/deps.py` 생성:

```python
from __future__ import annotations

"""내부 통신용 시크릿 검증"""

import os

from fastapi import Header, HTTPException


def verify_secret(x_internal_secret: str = Header(default="")) -> None:
    """Next.js → Python 내부 통신용 시크릿 검증"""
    expected = os.getenv("PYTHON_API_SECRET", "")
    if not expected:
        # 시크릿 미설정 시 개발 모드로 간주하여 통과
        return
    if x_internal_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid internal secret")
```

### 7.4 동작 확인

```bash
# 프로젝트 루트에서
uvicorn pyapi.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000/py/health` 를 열어서 아래 응답이 나오면 성공:

```json
{"status": "ok", "message": "D2trader Python API is running"}
```

`Ctrl+C`로 서버를 중단한다.

---

## 8. 환경변수 설정

### 8.1 프로젝트 루트 `.env`

기존 `.env`에 1줄 추가:

```bash
# ── 기존 (변경 없음) ──
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
KIS_ACCOUNT_PRODUCT=01
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# ── D2trader 추가 ──
PYTHON_API_SECRET=your-random-secret-here
```

시크릿 값 생성 (터미널에서):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# → 출력된 문자열을 PYTHON_API_SECRET에 붙여넣기
```

### 8.2 Next.js 환경변수 (`web/.env.local`)

`web/.env.local` 파일을 새로 생성:

```bash
# Python API 연결 (서버사이드 전용 — 브라우저에 노출 안 됨)
PYTHON_API_URL=http://localhost:8000
PYTHON_API_SECRET=your-random-secret-here
```

> `PYTHON_API_SECRET`은 루트 `.env`와 동일한 값을 사용한다.
> `NEXT_PUBLIC_` 접두사를 절대 붙이지 않는다 (브라우저 노출 방지).

### 8.3 .gitignore 확인

다음 항목이 `.gitignore`에 포함되어 있는지 확인:

```
.env
.env.local
web/.env.local
```

---

## 9. 개발 서버 실행

개발 시 **터미널 2개**를 동시에 띄운다.

### 터미널 1: Python API

```bash
# 프로젝트 루트에서
uvicorn pyapi.main:app --reload --port 8000
```

### 터미널 2: Next.js

```bash
# web/ 디렉토리에서
cd web
npm run dev
```

### 접속 확인

| URL | 용도 |
|-----|------|
| `http://localhost:3000` | Next.js 대시보드 (브라우저에서 열기) |
| `http://localhost:8000/py/health` | Python API 상태 확인 |
| `http://localhost:8000/docs` | FastAPI 자동 생성 API 문서 (Swagger UI) |

### 개발 워크플로우

```
1. 코드를 수정한다
2. 저장하면 Next.js (--turbo)와 FastAPI (--reload) 모두 자동 재시작
3. 브라우저에서 바로 확인
```

> `--reload`와 Turbopack 덕분에 대부분의 변경이 저장 즉시 반영된다.

---

## 10. Cloudflare 배포

> 이 단계는 로컬 개발이 완료된 후에 진행한다.
> 개발 단계에서는 건너뛰어도 된다.

### 10.1 사전 준비

- Cloudflare 계정 + 도메인 (이미 보유)
- `cloudflared` CLI 설치

```bash
# macOS
brew install cloudflared

# 로그인
cloudflared login
```

### 10.2 Python API — Cloudflare Tunnel

로컬 Python API를 인터넷에 노출한다:

```bash
# 터널 생성 (1회)
cloudflared tunnel create d2trader-api

# DNS 레코드 연결
cloudflared tunnel route dns d2trader-api api.d2trader.your-domain.com

# 설정 파일 생성: ~/.cloudflared/config.yml
```

`~/.cloudflared/config.yml` 내용:

```yaml
tunnel: d2trader-api
credentials-file: /Users/you/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: api.d2trader.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
```

터널 실행:

```bash
cloudflared tunnel run d2trader-api
```

### 10.3 Next.js — Cloudflare Pages

**방법 A: GitHub 연동 (자동 배포)**

1. GitHub에 push
2. Cloudflare Dashboard → Pages → "Create a project"
3. GitHub 레포 선택
4. 빌드 설정:
   - Framework: `Next.js`
   - Build command: `cd web && npm run build`
   - Build output: `web/.next`
   - Root directory: `/`
5. 환경변수 추가:
   - `PYTHON_API_URL` = `https://api.d2trader.your-domain.com`
   - `PYTHON_API_SECRET` = (루트 .env와 동일한 값)

**방법 B: CLI 배포 (수동)**

```bash
cd web
npm run build
npx wrangler pages deploy .next --project-name d2trader
```

### 10.4 배포 후 환경변수 변경

`web/.env.local`의 `PYTHON_API_URL`을 터널 URL로 변경:

```bash
# 로컬 개발:
PYTHON_API_URL=http://localhost:8000

# 배포 시 (Cloudflare Pages 환경변수로 설정):
PYTHON_API_URL=https://api.d2trader.your-domain.com
```

---

## 11. 트러블슈팅

### Node.js 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| `npx: command not found` | Node.js 미설치 또는 PATH 미설정 | `node -v` 확인, 재설치 |
| `Module not found` | 패키지 미설치 | `cd web && npm install` |
| 포트 3000 사용 중 | 다른 프로세스가 사용 | `lsof -i :3000`으로 확인, `kill <PID>` |
| `ERR_MODULE_NOT_FOUND` | import 경로 오류 | `@/` 별칭이 `tsconfig.json`에 설정되어 있는지 확인 |

### Python API 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| `ModuleNotFoundError: No module named 'src'` | sys.path에 프로젝트 루트 미포함 | `pyapi/main.py`의 `sys.path.insert` 확인 |
| `uvicorn: command not found` | uvicorn 미설치 | `pip3 install uvicorn` |
| 포트 8000 사용 중 | 다른 프로세스가 사용 | `lsof -i :8000`으로 확인, `kill <PID>` |
| Python API 응답 없음 | CORS 설정 누락 | `pyapi/main.py`에 CORS 미들웨어 확인 |

### 환경변수 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| KIS API 연결 실패 | `.env` 파일 누락 또는 잘못된 값 | `.env` 파일과 키 값 확인 |
| Python API 403 에러 | 시크릿 불일치 | `.env`와 `web/.env.local`의 시크릿이 동일한지 확인 |
| Next.js에서 환경변수 undefined | `.env.local` 파일 위치 또는 이름 오류 | `web/.env.local`이 `web/` 안에 있는지 확인 |

### Cloudflare 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| 터널 연결 안 됨 | cloudflared 미실행 | `cloudflared tunnel run d2trader-api` 실행 |
| Pages 빌드 실패 | 빌드 경로 오류 | `Root directory`와 `Build command` 확인 |
| API 호출 시 504 | Python 서버 다운 | 로컬 서버 + 터널 모두 실행 중인지 확인 |

---

## 퀵 레퍼런스: 주요 명령어 모음

```bash
# ── 프로젝트 셋업 (최초 1회) ──
npx create-next-app@latest web           # Next.js 프로젝트 생성
cd web && npx shadcn@latest init         # shadcn/ui 초기화
pip3 install fastapi uvicorn             # Python API 패키지

# ── 개발 서버 ──
uvicorn pyapi.main:app --reload --port 8000   # 터미널 1: Python API
cd web && npm run dev                          # 터미널 2: Next.js

# ── shadcn/ui 컴포넌트 추가 ──
cd web && npx shadcn@latest add [component]   # 예: npx shadcn@latest add alert

# ── npm 패키지 추가 ──
cd web && npm install [package]               # 예: npm install date-fns

# ── 빌드 확인 ──
cd web && npm run build                       # 프로덕션 빌드 테스트

# ── Cloudflare 배포 ──
cloudflared tunnel run d2trader-api           # Python API 터널
cd web && npx wrangler pages deploy .next     # Next.js 배포
```

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-18 | 초안 작성 — 11단계 셋업 가이드 |
