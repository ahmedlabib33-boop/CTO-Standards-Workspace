import { Pool, type PoolClient, type QueryResultRow } from "pg";

let pool: Pool | null = null;

export function getPool(): Pool | null {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) return null;
  if (!pool) {
    pool = new Pool({
      connectionString,
      max: Number(process.env.DB_POOL_MAX || 8),
      idleTimeoutMillis: 20_000,
      connectionTimeoutMillis: 4_000,
      ssl: process.env.DB_SSL === "false" ? undefined : { rejectUnauthorized: false },
    });
  }
  return pool;
}

export async function dbQuery<T extends QueryResultRow = QueryResultRow>(text: string, params: unknown[] = []) {
  const p = getPool();
  if (!p) throw new Error("DATABASE_URL is not configured");
  return p.query<T>(text, params);
}

export async function dbHealth(): Promise<{available:boolean; message:string}> {
  try {
    const p = getPool();
    if (!p) return { available: false, message: "PostgreSQL not configured; JSON corporate baseline remains active." };
    await p.query("select 1");
    return { available: true, message: "PostgreSQL online." };
  } catch (error) {
    return { available: false, message: `PostgreSQL unavailable: ${error instanceof Error ? error.message : String(error)}` };
  }
}

export async function withTransaction<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  const p = getPool();
  if (!p) throw new Error("DATABASE_URL is not configured");
  const client = await p.connect();
  try {
    await client.query("begin");
    const result = await fn(client);
    await client.query("commit");
    return result;
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    client.release();
  }
}
