export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

export type Market = "KR" | "US";
export type TradeSide = "BUY" | "SELL" | "CLOSE";
