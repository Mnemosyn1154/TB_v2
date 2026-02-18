import { type NextRequest } from "next/server";
import { pythonGet } from "@/lib/python-proxy";

/** 가격 배열 → 100 기준 정규화 */
function normalize(prices: number[]): number[] {
  if (prices.length === 0) return [];
  const base = prices[0];
  return prices.map((p) => +((p / base) * 100).toFixed(2));
}

/** 일별 수익률 배열 */
function dailyReturns(prices: number[]): number[] {
  const ret: number[] = [];
  for (let i = 1; i < prices.length; i++) {
    ret.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  return ret;
}

function mean(arr: number[]): number {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function std(arr: number[]): number {
  const m = mean(arr);
  return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length);
}

/** Beta = Cov(port, bench) / Var(bench) */
function calcBeta(portRet: number[], benchRet: number[]): number {
  const len = Math.min(portRet.length, benchRet.length);
  if (len < 2) return 0;
  const mp = mean(portRet.slice(0, len));
  const mb = mean(benchRet.slice(0, len));
  let cov = 0;
  let varB = 0;
  for (let i = 0; i < len; i++) {
    cov += (portRet[i] - mp) * (benchRet[i] - mb);
    varB += (benchRet[i] - mb) ** 2;
  }
  return varB === 0 ? 0 : cov / varB;
}

interface BenchmarkRaw {
  data: {
    kospi: { dates: string[]; prices: number[] };
    sp500: { dates: string[]; prices: number[] };
  };
  error: string | null;
}

export async function GET(request: NextRequest) {
  const period = request.nextUrl.searchParams.get("period") || "3M";

  try {
    const res = (await pythonGet(
      `/py/benchmark/data?period=${encodeURIComponent(period)}`
    )) as BenchmarkRaw;

    if (res.error) {
      return Response.json({ data: null, error: res.error }, { status: 500 });
    }

    const { kospi, sp500 } = res.data;

    // 날짜 기준은 KOSPI (거래일 기준)
    const dates = kospi.dates.length > 0 ? kospi.dates : sp500.dates;
    const kospiNorm = normalize(kospi.prices);
    const sp500Norm = normalize(sp500.prices);

    // 포트폴리오 시계열: 시뮬레이션 스냅샷 기반
    let portfolioNorm: number[];
    try {
      const portRes = (await pythonGet(
        `/py/benchmark/portfolio-series?period=${encodeURIComponent(period)}`
      )) as { data: { dates: string[]; values: number[] }; error: string | null };

      if (!portRes.error && portRes.data.dates.length >= 2) {
        // 스냅샷 날짜를 벤치마크 날짜에 맞추어 정렬
        const portMap = new Map<string, number>();
        portRes.data.dates.forEach((d, i) => portMap.set(d, portRes.data.values[i]));

        // dates에 매칭되는 값을 채우고, 없으면 이전 값으로 forward-fill
        const rawPort: number[] = [];
        let lastVal = portRes.data.values[0];
        for (const d of dates) {
          if (portMap.has(d)) lastVal = portMap.get(d)!;
          rawPort.push(lastVal);
        }
        portfolioNorm = normalize(rawPort);
      } else {
        // 스냅샷 없으면 fallback: 100 고정 (수평선)
        portfolioNorm = dates.map(() => 100);
      }
    } catch {
      portfolioNorm = dates.map(() => 100);
    }

    const portRet = dailyReturns(kospi.prices.map((_, i) => portfolioNorm[i] ?? 100));
    const kospiRet = dailyReturns(kospi.prices);
    const sp500Ret = dailyReturns(sp500.prices);

    const portfolioReturn = kospiNorm.length > 0
      ? +((portfolioNorm[portfolioNorm.length - 1] / 100 - 1) * 100).toFixed(2)
      : 0;
    const kospiReturn = kospiNorm.length > 0
      ? +((kospiNorm[kospiNorm.length - 1] / 100 - 1) * 100).toFixed(2)
      : 0;
    const sp500Return = sp500Norm.length > 0
      ? +((sp500Norm[sp500Norm.length - 1] / 100 - 1) * 100).toFixed(2)
      : 0;

    const beta = +calcBeta(portRet, kospiRet).toFixed(2);
    const alpha = +(portfolioReturn - beta * kospiReturn).toFixed(2);

    const trackingError = std(
      portRet.map((r, i) => r - (kospiRet[i] ?? 0))
    );
    const ir = trackingError > 0
      ? +((mean(portRet) - mean(kospiRet)) / trackingError * Math.sqrt(252)).toFixed(2)
      : 0;

    return Response.json({
      data: {
        dates,
        portfolio: portfolioNorm,
        kospi: kospiNorm,
        sp500: sp500Norm,
        metrics: {
          portfolio_return: portfolioReturn,
          kospi_return: kospiReturn,
          sp500_return: sp500Return,
          alpha,
          beta,
          information_ratio: ir,
        },
        strategy_comparison: [],
        period,
      },
      error: null,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Benchmark fetch failed";
    return Response.json({ data: null, error: msg }, { status: 500 });
  }
}
