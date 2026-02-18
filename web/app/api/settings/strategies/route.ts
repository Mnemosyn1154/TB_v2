import yaml from "js-yaml";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";

const SETTINGS_PATH = join(process.cwd(), "..", "config", "settings.yaml");

/** Default config templates per strategy type (enabled: false, complex fields empty) */
const TYPE_DEFAULTS: Record<string, Record<string, unknown>> = {
  stat_arb: {
    enabled: false,
    pairs: [],
    lookback_window: 60,
    entry_z_score: 2,
    exit_z_score: 0.5,
    stop_loss_z_score: 3.5,
    recalc_beta_days: 30,
    coint_pvalue: 0.05,
  },
  dual_momentum: {
    enabled: false,
    lookback_months: 12,
    rebalance_day: 1,
    kr_etf: "069500",
    us_etf: "SPY",
    us_etf_exchange: "NYS",
    safe_kr_etf: "148070",
    safe_us_etf: "SHY",
    safe_us_etf_exchange: "NYS",
    risk_free_rate: 0.04,
  },
  quant_factor: {
    enabled: false,
    top_n: 20,
    rebalance_months: 1,
    lookback_days: 252,
    momentum_days: 126,
    volatility_days: 60,
    min_data_days: 60,
    weights: { value: 0.3, quality: 0.3, momentum: 0.4 },
    universe_codes: [],
  },
};

export async function POST(request: Request) {
  try {
    const { key, type } = (await request.json()) as {
      key: string;
      type: string;
    };

    if (!key || !type) {
      return Response.json(
        { data: null, error: "key and type are required" },
        { status: 400 }
      );
    }

    if (!/^[a-z][a-z0-9_]*$/.test(key)) {
      return Response.json(
        {
          data: null,
          error: "key must be snake_case (lowercase letters, digits, underscores)",
        },
        { status: 400 }
      );
    }

    if (!TYPE_DEFAULTS[type]) {
      return Response.json(
        {
          data: null,
          error: `Unknown strategy type: ${type}. Available: ${Object.keys(TYPE_DEFAULTS).join(", ")}`,
        },
        { status: 400 }
      );
    }

    const content = await readFile(SETTINGS_PATH, "utf-8");
    const data = yaml.load(content) as Record<string, unknown>;
    const strategies = (data.strategies ?? {}) as Record<
      string,
      Record<string, unknown>
    >;

    if (strategies[key]) {
      return Response.json(
        { data: null, error: `Strategy '${key}' already exists` },
        { status: 409 }
      );
    }

    // Build new config: copy from existing instance of same type, or use defaults
    const existing = Object.values(strategies).find(
      (cfg) => (cfg.type ?? null) === null && TYPE_DEFAULTS[type]
        ? false
        : cfg.type === type
    );

    let newConfig: Record<string, unknown>;
    if (existing) {
      newConfig = structuredClone(existing) as Record<string, unknown>;
    } else {
      // Try copying from the canonical key (e.g. "stat_arb" for type "stat_arb")
      const canonical = strategies[type];
      if (canonical) {
        newConfig = structuredClone(canonical) as Record<string, unknown>;
      } else {
        newConfig = structuredClone(TYPE_DEFAULTS[type]);
      }
    }

    // Override: disabled, clear complex fields
    newConfig.enabled = false;
    newConfig.type = type;
    if (Array.isArray(newConfig.pairs)) newConfig.pairs = [];
    if (Array.isArray(newConfig.universe_codes)) newConfig.universe_codes = [];

    strategies[key] = newConfig;
    data.strategies = strategies;

    const updated = yaml.dump(data, { indent: 2, lineWidth: 120 });
    await writeFile(SETTINGS_PATH, updated, "utf-8");

    return Response.json({ data: { key, config: newConfig }, error: null });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 500 });
  }
}
