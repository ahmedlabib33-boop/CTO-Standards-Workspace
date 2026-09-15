export type AdminOverrides = {
  version: number;
  updated_at: string | null;
  activities: Record<string, Record<string, unknown>>;
  resources: Record<string, Record<string, unknown>>;
  rates: Record<string, Record<string, unknown>>;
  assumptions: Record<string, Record<string, unknown>>;
  additions: {
    activities: Record<string, unknown>[];
    resources: Record<string, unknown>[];
    rates: Record<string, unknown>[];
    assumptions: Record<string, unknown>[];
  };
  deletions: {
    activities: string[];
    resources: string[];
    rates: string[];
    assumptions: string[];
  };
  notes?: string;
};

export const emptyOverrides: AdminOverrides = {
  version: 1,
  updated_at: null,
  activities: {},
  resources: {},
  rates: {},
  assumptions: {},
  additions: { activities: [], resources: [], rates: [], assumptions: [] },
  deletions: { activities: [], resources: [], rates: [], assumptions: [] }
};
