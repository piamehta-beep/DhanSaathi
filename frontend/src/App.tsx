import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { queryCache, mutationCache } from "@/lib/net";
import { Welcome } from "@/screens/Welcome";
import { Home } from "@/screens/Home";
import { Recommend } from "@/screens/Recommend";
import { ScreenFallback } from "@/ui/Layout";

// Story-path screens load eagerly; supporting screens split out.
const Banks = lazy(() => import("@/screens/Banks").then((m) => ({ default: m.Banks })));
const Enquire = lazy(() => import("@/screens/Enquire").then((m) => ({ default: m.Enquire })));
const Why = lazy(() => import("@/screens/Why").then((m) => ({ default: m.Why })));
const Onboarding = lazy(() => import("@/screens/Onboarding").then((m) => ({ default: m.Onboarding })));
const Consent = lazy(() => import("@/screens/Consent").then((m) => ({ default: m.Consent })));

const client = new QueryClient({
  queryCache,
  mutationCache,
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 24 * 60 * 60_000, // keep the last successful responses for the offline state
      refetchOnWindowFocus: false,
      networkMode: "offlineFirst",
    },
    mutations: { networkMode: "offlineFirst" },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Suspense fallback={<ScreenFallback />}>
          <Routes>
            <Route path="/" element={<Welcome />} />
            <Route path="/start" element={<Onboarding />} />
            <Route path="/c/:id" element={<Home />} />
            <Route path="/c/:id/suggest" element={<Recommend />} />
            <Route path="/c/:id/banks" element={<Banks />} />
            <Route path="/c/:id/ask" element={<Enquire />} />
            <Route path="/c/:id/why" element={<Why />} />
            <Route path="/c/:id/data" element={<Consent />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
