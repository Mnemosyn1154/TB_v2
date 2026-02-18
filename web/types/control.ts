export type TradingMode = "paper" | "live";

export interface KillSwitchStatus {
  kill_switch: boolean;
}

export interface BotStatus {
  running: boolean;
  last_run_at: string | null;
  last_run_result: "success" | "error" | null;
  last_collect_at: string | null;
  last_collect_result: "success" | "error" | null;
  strategies: StrategyExecutionStatus[];
}

export interface StrategyExecutionStatus {
  name: string;
  key: string;
  last_run_at: string | null;
  status: "idle" | "running" | "success" | "error";
  error_message: string | null;
}

export interface LogEntry {
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR";
  message: string;
}
