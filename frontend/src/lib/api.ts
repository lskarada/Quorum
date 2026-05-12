import type { CaseInput, FinalVerdict } from "./types";

const API_BASE = "/api"; // Vite dev proxy forwards to http://localhost:8000

/**
 * Synchronous diagnose call. Returns the final verdict.
 *
 * Note: the backend currently raises NotImplementedError until Panel.diagnose()
 * is wired. This client function will resolve as soon as that lands.
 */
export async function diagnose(input: CaseInput): Promise<FinalVerdict> {
  const res = await fetch(`${API_BASE}/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new Error(`diagnose failed: ${res.status} ${res.statusText}`);
  }
  const body = (await res.json()) as { verdict: FinalVerdict };
  return body.verdict;
}
