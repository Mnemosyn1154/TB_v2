import { pythonGet } from "@/lib/python-proxy";

/** 가격 배열 → 100 기준 정규화 */
function normalize(prices: number[]): number[] {
  if (prices.length === 0) return [];
  const base = prices[0];
  return prices.map((p) => +((p / base) * 100).toFixed(2));
}

/** MDD 계산 (%) */
function calcMDD(values: number[]): number {
  let peak = values[0];
  let maxDd = 0;
  for (const v of values) {
    if (v > peak) peak = v;
    const dd = (v - peak) / peak;
    if (dd < maxDd) maxDd = dd;
  }
  return +(maxDd * 100).toFixed(2);
}

/** CAGR 계산 (%) */
function calcCAGR(first: number, last: number, years: number): number {
  if (years <= 0 || first <= 0) return 0;
  return +((Math.pow(last / first, 1 / years) - 1) * 100).toFixed(2);
}

interface BenchmarkRangeRaw {
  data: {
    kospi: { dates: string[]; prices: number[] };
    sp500: { dates: string[]; prices: number[] };
  };
  error: string | null;
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { start_date, end_date, equity_curve } = body as {
      start_date: string;
      end_date: string;
      equity_curve: { dates: string[]; values: number[] };
    };

    // Fetch benchmark data for the same date range
    const res = (await pythonGet(
      `/py/benchmark/data-range?start=${encodeURIComponent(start_date)}&end=${encodeURIComponent(end_date)}`
    )) as BenchmarkRangeRaw;

    if (res.error) {
      return Response.json({ data: null, error: res.error }, { status: 500 });
    }

    const { kospi, sp500 } = res.data;

    // Use backtest equity dates as the base timeline
    const dates = equity_curve.dates;
    const strategyValues = equity_curve.values;

    // Align benchmark data to backtest dates via forward-fill
    function alignToBaseDates(
      benchDates: string[],
      benchPrices: number[]
    ): number[] {
      if (benchDates.length === 0) return dates.map(() => 0);
      const priceMap = new Map<string, number>();
      benchDates.forEach((d, i) => priceMap.set(d, benchPrices[i]));

      const aligned: number[] = [];
      let lastVal = benchPrices[0];
      for (const d of dates) {
        if (priceMap.has(d)) lastVal = priceMap.get(d)!;
        aligned.push(lastVal);
      }
      return aligned;
    }

    const kospiAligned = alignToBaseDates(kospi.dates, kospi.prices);
    const sp500Aligned = alignToBaseDates(sp500.dates, sp500.prices);

    // Normalize all to 100 baseline
    const strategyNorm = normalize(strategyValues);
    const kospiNorm = normalize(kospiAligned);
    const sp500Norm = normalize(sp500Aligned);

    // Calculate years for CAGR
    const msPerYear = 365.25 * 24 * 60 * 60 * 1000;
    const years =
      (new Date(dates[dates.length - 1]).getTime() -
        new Date(dates[0]).getTime()) /
      msPerYear;

    // Compute comparison metrics
    const strategyReturn = strategyNorm.length > 0
      ? +(strategyNorm[strategyNorm.length - 1] - 100).toFixed(2)
      : 0;
    const kospiReturn = kospiNorm.length > 0
      ? +(kospiNorm[kospiNorm.length - 1] - 100).toFixed(2)
      : 0;
    const sp500Return = sp500Norm.length > 0
      ? +(sp500Norm[sp500Norm.length - 1] - 100).toFixed(2)
      : 0;

    const metrics = {
      strategy: {
        total_return: strategyReturn,
        cagr: calcCAGR(strategyValues[0], strategyValues[strategyValues.length - 1], years),
        mdd: calcMDD(strategyValues),
      },
      kospi: {
        total_return: kospiReturn,
        cagr: calcCAGR(kospiAligned[0], kospiAligned[kospiAligned.length - 1], years),
        mdd: calcMDD(kospiAligned),
      },
      sp500: {
        total_return: sp500Return,
        cagr: calcCAGR(sp500Aligned[0], sp500Aligned[sp500Aligned.length - 1], years),
        mdd: calcMDD(sp500Aligned),
      },
    };

    return Response.json({
      data: {
        dates,
        strategy: strategyNorm,
        kospi: kospiNorm,
        sp500: sp500Norm,
        metrics,
      },
      error: null,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Peer comparison fetch failed";
    return Response.json({ data: null, error: msg }, { status: 500 });
  }
}
