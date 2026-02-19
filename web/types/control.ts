export type TradingMode = "simulation" | "paper" | "live";

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

export interface SchedulerLastRun {
  time: string;
  status: "success" | "error" | "skipped";
  reason?: string;
  total_signals?: number;
  error?: string;
}

export interface SchedulerStatus {
  running: boolean;
  interval_minutes: number | null;
  next_run: string | null;
  last_run: SchedulerLastRun | null;
}

export interface FullBotStatus {
  kill_switch: boolean;
  scheduler: SchedulerStatus;
  mode: TradingMode;
}

export interface LogEntry {
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR";
  message: string;
}
