export type Session = { token: string; customerId: string | null };

const TOKEN = "dhansaathi_token";
const CUSTOMER = "dhansaathi_customer_id";

function payload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split(".")[1];
    return JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/"))) as Record<string, unknown>;
  } catch { return null; }
}

export function saveSession(token: string) {
  localStorage.setItem(TOKEN, token);
  const id = payload(token)?.customer_id;
  if (typeof id === "string" && id) localStorage.setItem(CUSTOMER, id);
}

export function setCustomerId(id: string) { localStorage.setItem(CUSTOMER, id); }
export function session(): Session | null {
  const token = localStorage.getItem(TOKEN);
  return token ? { token, customerId: localStorage.getItem(CUSTOMER) } : null;
}
export function signOut() { localStorage.removeItem(TOKEN); localStorage.removeItem(CUSTOMER); }
