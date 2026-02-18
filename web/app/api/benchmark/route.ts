import { type NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const period = request.nextUrl.searchParams.get("period") || "3M";

  // TODO: yahoo-finance2를 사용한 벤치마크 데이터 조회
  // 현재는 플레이스홀더 응답
  return Response.json({
    data: {
      dates: [],
      portfolio: [],
      kospi: [],
      sp500: [],
      metrics: {
        portfolio_return: 0,
        kospi_return: 0,
        sp500_return: 0,
        alpha: 0,
        beta: 0,
        information_ratio: 0,
      },
      strategy_comparison: [],
      period,
    },
    error: null,
  });
}
