import fs from "node:fs";
import path from "node:path";

export type SamcoAvailability = {
  excel_baseline: boolean;
  historical_data: boolean;
  live_project_data: boolean;
  fallback_active: boolean;
};

export type SamcoBundle = {
  schema_version: string | null;
  generated_at: string | null;
  mode: "baseline_only" | "hybrid_predictive" | "empty_safe_mode" | string;
  availability: SamcoAvailability;
  counts: Record<string, number>;
  datasets: {
    activities: Record<string, unknown>[];
    resources: Record<string, unknown>[];
    rates: Record<string, unknown>[];
    commercial_assumptions: Record<string, unknown>[];
  };
};

const EMPTY: SamcoBundle = {
  schema_version: null,
  generated_at: null,
  mode: "empty_safe_mode",
  availability: {
    excel_baseline: false,
    historical_data: false,
    live_project_data: false,
    fallback_active: true
  },
  counts: { activities: 0, resources: 0, rates: 0, assumptions: 0, workbooks: 0 },
  datasets: { activities: [], resources: [], rates: [], commercial_assumptions: [] }
};

export function readJsonSafe<T>(relativePath: string, fallback: T): T {
  try {
    const full = path.join(process.cwd(), relativePath);
    return JSON.parse(fs.readFileSync(full, "utf8")) as T;
  } catch {
    return fallback;
  }
}

export function getFixedDataBundle(): SamcoBundle {
  return readJsonSafe<SamcoBundle>("data/generated/master/fixed_data.bundle.json", EMPTY);
}

export function getDataMode(bundle = getFixedDataBundle()) {
  const hasBaseline = bundle.availability.excel_baseline;
  const hasHistory = bundle.availability.historical_data;
  const hasLive = bundle.availability.live_project_data;
  if (!hasBaseline) {
    return {
      mode: "empty_safe_mode" as const,
      prediction: "disabled",
      message: "App online. Corporate JSON baseline has not been generated yet."
    };
  }
  if (!hasHistory && !hasLive) {
    return {
      mode: "baseline_only" as const,
      prediction: "corporate_rules_and_excel_baseline",
      message: "Corporate baseline active. Historical and live-project data are optional."
    };
  }
  return {
    mode: "hybrid_predictive" as const,
    prediction: "baseline_plus_available_project_evidence",
    message: "Corporate baseline enriched by optional project evidence."
  };
}
