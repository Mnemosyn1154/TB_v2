/** snake_case → Title Case (e.g. "stat_arb" → "Stat Arb") */
export function snakeToTitle(s: string): string {
  return s
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Well-known Korean labels for common parameter fields */
const KNOWN_LABELS: Record<string, string> = {
  lookback_window: "룩백 윈도우 (일)",
  entry_z_score: "진입 Z-Score",
  exit_z_score: "청산 Z-Score",
  stop_loss_z_score: "손절 Z-Score",
  recalc_beta_days: "헤지 비율 재계산 주기 (일)",
  coint_pvalue: "공적분 p-value 임계값",
  lookback_months: "룩백 기간 (월)",
  rebalance_day: "리밸런싱 거래일",
  risk_free_rate: "무위험수익률 (연)",
  top_n: "상위 N종목",
  rebalance_months: "리밸런싱 주기 (월)",
  lookback_days: "Value 룩백 (거래일)",
  momentum_days: "Momentum 룩백 (거래일)",
  volatility_days: "변동성 윈도우 (일)",
};

export function fieldLabel(field: string): string {
  return KNOWN_LABELS[field] ?? snakeToTitle(field);
}

/** Fields to exclude from numeric param extraction */
const EXCLUDED_FIELDS = new Set([
  "enabled",
  "type",
  "pairs",
  "universe_codes",
  "weights",
]);

/** Extract editable numeric params from a strategy config */
export function extractNumericParams(
  config: Record<string, unknown>
): { field: string; label: string; value: number }[] {
  return Object.entries(config)
    .filter(
      ([key, val]) => typeof val === "number" && !EXCLUDED_FIELDS.has(key)
    )
    .map(([field, val]) => ({
      field,
      label: fieldLabel(field),
      value: val as number,
    }));
}

/** Auto-summarize a strategy config: show top numeric params as "label: value" */
export function summarizeConfig(config: Record<string, unknown>): string {
  const params = extractNumericParams(config);
  return params
    .slice(0, 4)
    .map((p) => `${p.label}: ${p.value}`)
    .join(" · ");
}
