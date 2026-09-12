// Thin typed client around fetch. Same-origin in dev (Vite proxy); honours
// VITE_API_BASE when set. Every handled backend error is {detail: {error, ...}}.
import type { components } from "./types";

type S = components["schemas"];
export type CustomerSummary = S["CustomerSummary"];
export type CustomerDetail = S["CustomerDetail"];
export type FeaturesResponse = S["FeaturesResponse"];
export type DistressRiskResponse = S["DistressRiskResponse"];
export type AnomalyListResponse = S["AnomalyListResponse"];
export type AnomalyItem = S["AnomalyItem"];
export type RecommendationResponse = S["RecommendationResponse"];
export type MatchingProductsResponse = S["MatchingProductsResponse"];
export type BankProductMatch = S["BankProductMatch"];
export type EnquiryRequest = S["EnquiryRequest"];
export type EnquiryResponse = S["EnquiryResponse"];
export type CounterOffer = S["CounterOffer"];
export type ExplainResponse = S["ExplainResponse"];
export type Attribution = S["Attribution"];
export type ConsentListResponse = S["ConsentListResponse"];
export type ConsentRecordOut = S["ConsentRecordOut"];
export type ConsentCreated = S["ConsentCreated"];
export type ConsentRevoked = S["ConsentRevoked"];
export type HealthResponse = S["HealthResponse"];
export type OnboardingStartResponse = S["OnboardingStartResponse"];
export type OnboardingMessageResponse = S["OnboardingMessageResponse"];
export type SimulateRequest = Partial<S["SimulateRequest"]> & { scenarios: string[] };
export type SimulateResponse = S["SimulateResponse"];
export type SimulationScenario = S["SimulationScenario"];
export type TransactionListResponse = S["TransactionListResponse"];
export type TransactionItem = S["TransactionItem"];
export type AuditLogResponse = S["AuditLogResponse"];
export type AuditLogItem = S["AuditLogItem"];
export type NewTransaction = S["NewTransaction"];
export type TransactionCreated = S["TransactionCreated"];

const BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? "").replace(/\/$/, "");
const API = BASE.endsWith("/api/v1") ? BASE : `${BASE}/api/v1`;

export type AuthResponse = { access_token: string; token_type: string };
export type AuthUser = { id: string; email: string; customer_id: string | null };
export type ManualCustomer = { customer_id: string; created: boolean };
export type ChatResponse = { reply: string; tool: string | null; data?: Record<string, unknown> };
export type SupportRequest = { id: string; reason: string; recommendation_id: string | null; message: string; linked_audit_log_id: string | null; status: "open" | "resolved"; created_at: string | null };

const token = () => localStorage.getItem("dhansaathi_token");

export class ApiError extends Error {
  status: number;
  code: string;
  detail: unknown;
  missingScopes: string[];
  constructor(status: number, detail: unknown) {
    const d = (detail ?? {}) as Record<string, unknown>;
    const code = typeof d.error === "string" ? d.error : status === 422 ? "validation_error" : `http_${status}`;
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.missingScopes = Array.isArray(d.missing_scopes) ? (d.missing_scopes as string[]) : [];
  }
  get isConsent() { return this.status === 403 && this.code === "consent_required"; }
  get isNotFound() { return this.status === 404; }
  get isValidation() { return this.status === 422; }
}

export class NetworkError extends Error {
  constructor() { super("network"); this.name = "NetworkError"; }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(token() ? { authorization: `Bearer ${token()}` } : {}), ...(init?.headers ?? {}) },
    });
  } catch {
    throw new NetworkError();
  }
  if (!res.ok) {
    let body: unknown = null;
    try { body = await res.json(); } catch { /* non-JSON error body */ }
    const detail = body && typeof body === "object" && "detail" in body ? (body as { detail: unknown }).detail : body;
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const q = (params: Record<string, string | number | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const api = {
  signup: (email: string, password: string) =>
    request<AuthUser>("/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  setupMe: (body: { name: string; age: number; city: string; state: string; monthly_income_mean: number; preferred_language: string }) =>
    request<ManualCustomer>("/customers/me/setup", { method: "POST", body: JSON.stringify(body) }),
  addIncome: (body: { amount: number; credit_day: number }) =>
    request<{ customer_id: string }>("/customers/me/income", { method: "POST", body: JSON.stringify(body) }),
  addObligation: (body: { amount: number; day_of_month: number; type: "rent" | "emi" | "insurance_premium" | "sip" }) =>
    request<{ id: string }>("/customers/me/obligations", { method: "POST", body: JSON.stringify(body) }),
  addManualTransaction: (body: { date: string; amount: number; type: "credit" | "debit"; category: string; merchant: string }) =>
    request<{ id: string }>("/customers/me/transactions", { method: "POST", body: JSON.stringify(body) }),
  chat: (body: { customer_id: string; message: string; language: string }) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),
  supportRequests: (id: string) => request<{ customer_id: string; support_requests: SupportRequest[] }>(`/customers/${id}/support-requests`),
  createSupportRequest: (id: string, body: { reason: string; recommendation_id?: string | null; message: string }) =>
    request<SupportRequest>(`/customers/${id}/support-request`, { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthResponse>("/health"),

  customers: (params: { persona?: string; limit?: number; offset?: number }) =>
    request<S["CustomerListResponse"]>(`/customers${q(params)}`),
  customer: (id: string) => request<CustomerDetail>(`/customers/${id}`),
  features: (id: string) => request<FeaturesResponse>(`/customers/${id}/features`),
  distressRisk: (id: string) => request<DistressRiskResponse>(`/customers/${id}/distress-risk`),
  anomalies: (id: string, params: { min_score?: number; limit?: number }) =>
    request<AnomalyListResponse>(`/customers/${id}/anomalies${q(params)}`),

  simulate: (id: string, body: SimulateRequest) =>
    request<SimulateResponse>(`/customers/${id}/simulate`, { method: "POST", body: JSON.stringify(body) }),
  transactions: (id: string, params: { category?: string; limit?: number; offset?: number; start_date?: string; end_date?: string }) =>
    request<TransactionListResponse>(`/customers/${id}/transactions${q(params)}`),
  createTransaction: (id: string, body: NewTransaction) =>
    request<TransactionCreated>(`/customers/${id}/transactions`, { method: "POST", body: JSON.stringify(body) }),
  recommendWithLLM: (id: string, language: string) =>
    request<RecommendationResponse>(`/customers/${id}/recommend`, {
      method: "POST", body: JSON.stringify({ language, include_llm_explanation: true }),
    }),
  audit: (id: string, params: { action?: string; limit?: number; offset?: number }) =>
    request<AuditLogResponse>(`/audit/${id}${q(params)}`),

  recommend: (id: string, language: string) =>
    request<RecommendationResponse>(`/customers/${id}/recommend`, {
      method: "POST", body: JSON.stringify({ language }),
    }),
  matchingProducts: (id: string, recId: string) =>
    request<MatchingProductsResponse>(`/customers/${id}/matching-products/${recId}`),
  enquire: (id: string, body: EnquiryRequest) =>
    request<EnquiryResponse>(`/customers/${id}/enquire`, { method: "POST", body: JSON.stringify(body) }),
  explain: (id: string, recId: string) => request<ExplainResponse>(`/customers/${id}/explain/${recId}`),

  consent: (id: string) => request<ConsentListResponse>(`/customers/${id}/consent`),
  grantConsent: (body: S["ConsentRequest"]) =>
    request<ConsentCreated>("/consent", { method: "POST", body: JSON.stringify(body) }),
  revokeConsent: (consentId: string) =>
    request<ConsentRevoked>(`/consent/${consentId}/revoke`, { method: "POST" }),

  onboardingStart: (language: string) =>
    request<OnboardingStartResponse>("/onboarding/start", { method: "POST", body: JSON.stringify({ language }) }),
  onboardingMessage: (sessionId: string, message: string) =>
    request<OnboardingMessageResponse>(`/onboarding/${sessionId}/message`, {
      method: "POST", body: JSON.stringify({ message }),
    }),
};
