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
  };
  const grant = useMutation({
    mutationFn: (body: { scope: string; purpose: string }) =>
      api.grantConsent({ customer_id: id, scope: body.scope, granted: true, purpose: body.purpose }),
    onSuccess: invalidateAll,
  });
  const revoke = useMutation({ mutationFn: (consentId: string) => api.revokeConsent(consentId), onSuccess: invalidateAll });
  return { grant, revoke };
}
