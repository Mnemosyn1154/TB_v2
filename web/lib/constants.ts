/** 차트 색상 팔레트 */
export const CHART_COLORS = {
  blue: "#3b82f6",
  emerald: "#10b981",
  purple: "#a855f7",
  orange: "#f59e0b",
  pink: "#ec4899",
  teal: "#14b8a6",
  red: "#ef4444",
  gray: "#6b7280",
} as const;

/** 시장별 색상 */
export const MARKET_COLORS = {
  KR: CHART_COLORS.blue,
  US: CHART_COLORS.emerald,
} as const;

/** 탭 정의 */
export const TABS = [
  { key: "portfolio", label: "자산 현황", icon: "BarChart3" },
  { key: "benchmark", label: "벤치마크", icon: "TrendingUp" },
  { key: "strategy", label: "전략 설정", icon: "Settings" },
  { key: "backtest", label: "백테스트", icon: "FlaskConical" },
  { key: "paper", label: "모의거래", icon: "TestTube2" },
  { key: "control", label: "실행 & 제어", icon: "Play" },
] as const;

export type TabKey = (typeof TABS)[number]["key"];

/** 기본값 */
export const DEFAULTS = {
  POLLING_INTERVAL: 5 * 60 * 1000, // 5분
  INITIAL_CAPITAL: 50_000_000,
  BENCHMARK_PERIOD: "3M" as const,
} as const;
