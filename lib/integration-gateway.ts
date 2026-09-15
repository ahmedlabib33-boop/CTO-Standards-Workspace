export type IntegrationName = "project_intake" | "github" | "vercel" | "primavera" | "sap" | "microsoft365" | "powerbi";

const ENV_MAP: Record<IntegrationName, string[]> = {
  project_intake: ["SAMCO_INGESTION_API_URL", "NEXT_PUBLIC_INGESTION_API_URL"],
  github: ["GITHUB_REPOSITORY"],
  vercel: ["VERCEL_DEPLOY_HOOK_URL"],
  primavera: ["PRIMAVERA_API_URL"],
  sap: ["SAP_API_URL"],
  microsoft365: ["MICROSOFT365_API_URL"],
  powerbi: ["POWERBI_API_URL"],
};

export function integrationStatus() {
  return Object.entries(ENV_MAP).map(([name, keys]) => ({
    name,
    configured: keys.some((k) => Boolean(process.env[k])),
    required_for_core: false,
  }));
}
