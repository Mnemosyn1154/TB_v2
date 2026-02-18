# Code Conventions

## Python

### 파일 구조

```python
from __future__ import annotations           # 모든 .py 첫 줄

"""
모듈 설명

Depends on: src.core.config, src.core.broker
Used by: pyapi.routers.portfolio
Modification Guide:
    - 새 메서드 추가 시 XXX 확인
"""

from loguru import logger                     # 로깅
from src.core.config import get_config        # 설정 접근 (싱글턴)
```

### API 라우터 패턴 (pyapi/)

```python
# pyapi/routers/example.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from pyapi.deps import verify_secret

router = APIRouter(prefix="/py/example", tags=["example"])

@router.get("/")
def get_example(secret: None = Depends(verify_secret)):
    # Lazy import — 핸들러 함수 내부에서만 import (순환 참조 방지)
    from dashboard.services.example_service import get_data
    try:
        result = get_data()
        return {"data": result, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}
```

핵심 규칙:
- `dashboard/services/` 경유, `src/` 직접 import 지양
- 응답 envelope: `{"data": T | null, "error": string | null}`
- `Depends(verify_secret)`로 인증
- `try/except`로 에러를 envelope에 포함

### DB 패턴

```python
from sqlalchemy import create_engine, text

engine = create_engine(f"sqlite:///{db_path}")
with engine.connect() as conn:
    conn.execute(text("INSERT OR IGNORE INTO ..."))  # 멱등 쓰기
    df = pd.read_sql(text("SELECT ..."), conn)       # DataFrame 읽기
    conn.commit()
```

- SQLAlchemy + raw SQL (`text()`), ORM 미사용
- SQLite: `data/trading_bot.db`
- `INSERT OR IGNORE`로 중복 방지

### 전략 패턴

```python
from src.strategies.base import BaseStrategy, TradeSignal, Signal

class NewStrategy(BaseStrategy):
    def prepare(self, prices: dict) -> None: ...
    def generate_signals(self) -> list[TradeSignal]: ...
    def get_status(self) -> dict: ...
    def get_universe(self) -> list[dict]: ...
    def get_pairs(self) -> list[str]: ...
```

- 전략은 순수 로직: I/O, 브로커 접근, DB 접근 없음
- `config_key`로 settings.yaml에서 파라미터 로드
- `STRATEGY_REGISTRY`에 등록 필수

---

## TypeScript / React

### 컴포넌트 구조

```
components/{domain}/
├── {domain}-tab.tsx        # 탭 컨테이너 (데이터 페칭, 레이아웃)
├── {feature-a}.tsx         # 하위 컴포넌트 A
└── {feature-b}.tsx         # 하위 컴포넌트 B
```

- `"use client"` 디렉티브: 인터랙티브 컴포넌트에 필수
- `components/ui/` 하위: shadcn/ui 생성 파일, 수정 금지
- UI 텍스트: 한국어 / 코드 및 주석: 영어

### 데이터 페칭 패턴

```typescript
// hooks/use-example.ts
import { useApi } from "@/hooks/use-api";
import { getExample } from "@/lib/api-client";
import type { ExampleData } from "@/types/example";

export function useExample() {
  return useApi<ExampleData>(getExample);
  // 반환: { data, error, loading, lastUpdated, refetch }
}
```

### API 클라이언트 패턴

```typescript
// lib/api-client.ts
async function fetchApi<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  return res.json();
}

export const getExample = () => fetchApi("/example");
export const createExample = (data: unknown) =>
  fetchApi("/example", { method: "POST", body: JSON.stringify(data) });
```

### API Route 프록시 패턴

```typescript
// app/api/example/route.ts
import { pythonGet } from "@/lib/python-proxy";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const data = await pythonGet("/py/example");
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ data: null, error: String(e) }, { status: 502 });
  }
}
```

### 타입 정의

```typescript
// types/common.ts
export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}
export type Market = "KR" | "US";
export type TradeSide = "BUY" | "SELL" | "CLOSE";
```

도메인별 파일: `types/portfolio.ts`, `types/backtest.ts`, `types/paper.ts`, 등.

---

## 스타일링

- Tailwind CSS 4 유틸리티 클래스
- OKLCH 색상 시스템: `globals.css`에서 CSS 변수로 정의
- 다크 모드 기본: `ThemeProvider defaultTheme="dark"`
- 반응형 breakpoints: Tailwind 기본값 사용
- Geist 폰트: `next/font`로 로드
