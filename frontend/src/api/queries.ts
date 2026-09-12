// TanStack Query hooks. Keys are stable per customer so switching persona in
// the header swaps the whole cache slice; the last successful response stays
// visible when the network drops (brief §11).
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, NetworkError } from "./client";

export const keys = {
  health: ["health"] as const,
  customers: (persona?: string) => ["customers", persona ?? "all"] as const,
  customer: (id: string) => ["customer", id] as const,
  features: (id: string) => ["features", id] as const,
  distress: (id: string) => ["distress", id] as const,
  anomalies: (id: string) => ["anomalies", id] as const,
  recommend: (id: string, lang: string) => ["recommend", id, lang] as const,
  matching: (id: string, rec: string) => ["matching", id, rec] as const,
  explain: (id: string, rec: string) => ["explain", id, rec] as const,
  consent: (id: string) => ["consent", id] as const,
  simulate: (id: string, key: string) => ["simulate", id, key] as const,
  transactions: (id: string, category: string, offset: number) => ["transactions", id, category, offset] as const,
  audit: (id: string, offset: number) => ["audit", id, offset] as const,
};

// Don't retry things that won't change on retry.
export const retryPolicy = (count: number, err: unknown) => {
  if (err instanceof ApiError) return false;
  if (err instanceof NetworkError) return count < 1;
  return count < 2;
};

export function useHealth() {
  return useQuery({
    queryKey: keys.health,
    queryFn: api.health,
    refetchInterval: (query) => (query.state.data?.models.status === "warm" ? false : 3000),
    retry: retryPolicy,
  });
}

export const useCustomers = (persona?: string, limit = 6) =>
  useQuery({ queryKey: [...keys.customers(persona), limit], queryFn: () => api.customers({ persona, limit }), retry: retryPolicy, staleTime: 5 * 60_000 });

export const useCustomer = (id: string, enabled = true) =>
  useQuery({ queryKey: keys.customer(id), queryFn: () => api.customer(id), retry: retryPolicy, staleTime: 5 * 60_000, enabled });

export const useFeatures = (id: string) =>
  useQuery({ queryKey: keys.features(id), queryFn: () => api.features(id), retry: retryPolicy });

export const useDistress = (id: string) =>
  useQuery({ queryKey: keys.distress(id), queryFn: () => api.distressRisk(id), retry: retryPolicy });

export const useAnomalies = (id: string) =>
  useQuery({
    queryKey: keys.anomalies(id),
    queryFn: () => api.anomalies(id, { min_score: 0.7, limit: 3 }),
    retry: retryPolicy,
  });

// The recommendation is a POST but semantically a read for this customer; we
// cache it as a query so S2/S3/S5 share one recommendation_id.
export const useRecommendation = (id: string, lang: string) =>
  useQuery({
    queryKey: keys.recommend(id, lang),
    queryFn: () => api.recommend(id, lang),
    retry: retryPolicy,
    staleTime: 10 * 60_000,
  });

export const useMatching = (id: string, rec: string | undefined) =>
  useQuery({
    queryKey: keys.matching(id, rec ?? ""),
    queryFn: () => api.matchingProducts(id, rec!),
    enabled: !!rec,
    retry: retryPolicy,
    staleTime: 10 * 60_000,
  });

export const useExplain = (id: string, rec: string | undefined) =>
  useQuery({
    queryKey: keys.explain(id, rec ?? ""),
    queryFn: () => api.explain(id, rec!),
    enabled: !!rec,
    retry: retryPolicy,
    staleTime: 10 * 60_000,
  });

// Monte Carlo runs are deterministic (seed 42) so they cache well per input.
export type LoanScenario = { amount: number; tenure: number; rate: number } | null;
export type SimOptions = { months?: number; paths?: number };
export const useSimulation = (id: string, loan: LoanScenario, enabled = true, opts: SimOptions = {}) => {
  const body = {
    ...(loan
      ? { scenarios: ["baseline", "take_loan", "smaller_loan"], loan_amount: loan.amount, loan_tenure_months: loan.tenure, loan_interest_rate: loan.rate }
      : { scenarios: ["baseline"] }),
    ...(opts.months ? { months_projected: opts.months } : {}),
    ...(opts.paths ? { n_paths: opts.paths } : {}),
  };
  return useQuery({
    queryKey: keys.simulate(id, JSON.stringify(body)),
    queryFn: () => api.simulate(id, body),
    enabled,
    retry: retryPolicy,
    staleTime: 30 * 60_000,
  });
};

export const useTransactions = (id: string, category: string, offset: number, limit = 40, startDate?: string) =>
  useQuery({
    queryKey: [...keys.transactions(id, category, offset), limit, startDate ?? ""],
    queryFn: () => api.transactions(id, { category: category === "all" ? undefined : category, limit, offset, start_date: startDate }),
    retry: retryPolicy,
    placeholderData: (prev) => prev,
  });

export const useAllAnomalies = (id: string) =>
  useQuery({ queryKey: ["anomalies-all", id], queryFn: () => api.anomalies(id, { min_score: 0.5, limit: 50 }), retry: retryPolicy });

export const useAudit = (id: string, offset: number, limit = 25, action?: string) =>
  useQuery({
    queryKey: [...keys.audit(id, offset), limit, action ?? ""],
    queryFn: () => api.audit(id, { limit, offset, action }),
    retry: retryPolicy,
    placeholderData: (prev) => prev,
  });

export const useCustomerPage = (persona: string | undefined, offset: number, limit = 12) =>
  useQuery({
    queryKey: ["customers-page", persona ?? "all", offset, limit],
    queryFn: () => api.customers({ persona, limit, offset }),
    retry: retryPolicy,
    staleTime: 10 * 60_000,
    placeholderData: (prev) => prev,
  });

// Optional LLM wording; a separate key so the structured recommendation
// (and its recommendation_id) is never replaced by this call.
export const useLLMExplanation = (id: string, lang: string, enabled: boolean) =>
  useQuery({
    queryKey: ["recommend-llm", id, lang],
    queryFn: () => api.recommendWithLLM(id, lang),
    enabled,
    retry: retryPolicy,
    staleTime: 10 * 60_000,
  });

// Appending a transaction changes everything derived from it. Drop the
// customer's whole cache slice so every screen re-reads.
export function useAddTransaction(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.createTransaction>[1]) => api.createTransaction(id, body),
    onSuccess: () => {
      for (const k of ["features", "distress", "anomalies", "anomalies-all", "recommend", "recommend-llm", "matching", "explain", "simulate", "transactions", "audit"]) {
        qc.removeQueries({ queryKey: [k, id] });
      }
      qc.invalidateQueries({ queryKey: keys.customer(id) });
    },
  });
}

export const useConsent = (id: string) =>
  useQuery({ queryKey: keys.consent(id), queryFn: () => api.consent(id), retry: retryPolicy });

export function useEnquire(id: string) {
  return useMutation({ mutationFn: (body: Parameters<typeof api.enquire>[1]) => api.enquire(id, body) });
}

export function useConsentMutations(id: string) {
  const qc = useQueryClient();
  const invalidateAll = () => {
    // Consent changes what every other endpoint returns. Drop everything for
    // this customer so a revoked scope shows its 403 honestly.
    qc.invalidateQueries({ queryKey: keys.consent(id) });
    qc.removeQueries({ queryKey: keys.features(id) });
    qc.removeQueries({ queryKey: keys.distress(id) });
    qc.removeQueries({ queryKey: keys.anomalies(id) });
    qc.removeQueries({ queryKey: ["recommend", id] });
    qc.removeQueries({ queryKey: ["matching", id] });
    qc.removeQueries({ queryKey: ["explain", id] });
    qc.removeQueries({ queryKey: ["simulate", id] });
    qc.removeQueries({ queryKey: ["audit", id] });
    qc.removeQueries({ queryKey: ["anomalies-all", id] });
  };
  const grant = useMutation({
    mutationFn: (body: { scope: string; purpose: string }) =>
      api.grantConsent({ customer_id: id, scope: body.scope, granted: true, purpose: body.purpose }),
    onSuccess: invalidateAll,
  });
  const revoke = useMutation({ mutationFn: (consentId: string) => api.revokeConsent(consentId), onSuccess: invalidateAll });
  return { grant, revoke };
}
