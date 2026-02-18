import { type NextRequest } from "next/server";
import YahooFinance from "yahoo-finance2";

const yahooFinance = new (YahooFinance as any)();

const PERIOD_DAYS: Record<string, number> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  ALL: 365 * 3,
};

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10);
}

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

async function fetchHistory(symbol: string, startDate: Date, endDate: Date) {
  try {
    const result = await yahooFinance.chart(symbol, {
      period1: startDate,
      period2: endDate,
      interval: "1d",
    });
    const quotes = result.quotes ?? [];
    const dates: string[] = [];
    const prices: number[] = [];
    for (const q of quotes) {
      if (q.close != null && q.date) {
        dates.push(toDateStr(new Date(q.date)));
        prices.push(q.close);
      }
    }
    return { dates, prices };
  } catch {
    return { dates: [] as string[], prices: [] as number[] };
  }
}

export async function GET(request: NextRequest) {
  const period = request.nextUrl.searchParams.get("period") || "3M";
  const days = PERIOD_DAYS[period] ?? 90;

  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(endDate.getDate() - days);

  try {
    const [kospi, sp500] = await Promise.all([
      fetchHistory("^KS11", startDate, endDate),
      fetchHistory("^GSPC", startDate, endDate),
    ]);

    // 날짜 기준은 KOSPI (거래일 기준)
    const dates = kospi.dates.length > 0 ? kospi.dates : sp500.dates;
    const kospiNorm = normalize(kospi.prices);
    const sp500Norm = normalize(sp500.prices);

    // 포트폴리오 수익률은 아직 시계열이 없으므로 KOSPI 기준 +alpha 시뮬레이션
    // TODO: 실제 포트폴리오 시계열 연동
    const portfolioNorm = kospiNorm.map((v) => +(v * 1.02).toFixed(2));

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
