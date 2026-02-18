import type { Market, TradeSide } from "./common";

export interface PaperSession {
  session_id: string;
  start_date: string;
  end_date: string | null;
  status: "active" | "stopped";
  strategy_names: string[];
}

export interface PaperSignal {
  strategy: string;
  code: string;
  market: Market;
  signal: string;
  quantity: number;
  price: number;
  reason: string;
}

export interface PaperTrade {
  strategy: string;
  code: string;
  market: Market;
  side: TradeSide;
  quantity: number;
  price: number;
  reason: string;
  timestamp: string;
}
