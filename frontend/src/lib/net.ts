// Tiny offline store fed by the query cache and the browser's online events.
// "Offline" here means "the last request to the backend failed to connect",
// which covers both no network and a stopped backend.
import { useSyncExternalStore } from "react";
import { QueryCache, MutationCache } from "@tanstack/react-query";
import { NetworkError } from "@/api/client";

let offline = false;
const listeners = new Set<() => void>();
const set = (v: boolean) => { if (offline !== v) { offline = v; listeners.forEach((l) => l()); } };

export const useOffline = () =>
  useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l); }, () => offline);

export const markOffline = () => set(true);
export const markOnline = () => set(false);

export const queryCache = new QueryCache({
  onError: (err) => { if (err instanceof NetworkError) set(true); },
  onSuccess: () => set(false),
});
export const mutationCache = new MutationCache({
  onError: (err) => { if (err instanceof NetworkError) set(true); },
  onSuccess: () => set(false),
});

if (typeof window !== "undefined") {
  window.addEventListener("offline", () => set(true));
  window.addEventListener("online", () => set(false));
}
