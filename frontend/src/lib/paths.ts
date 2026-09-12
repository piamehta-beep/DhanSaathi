export const paths = {
  welcome: "/",
  onboarding: "/start",
  about: "/how-it-works",
  home: (id: string) => `/c/${id}`,
  suggest: (id: string) => `/c/${id}/suggest`,
  banks: (id: string) => `/c/${id}/banks`,
  ask: (id: string) => `/c/${id}/ask`,
  why: (id: string) => `/c/${id}/why`,
  data: (id: string, scope?: string) => `/c/${id}/data${scope ? `?scope=${scope}` : ""}`,
  future: (id: string, loan?: { amount: number; tenure: number }) =>
    `/c/${id}/future${loan ? `?amount=${loan.amount}&tenure=${loan.tenure}` : ""}`,
  money: (id: string) => `/c/${id}/money`,
  trail: (id: string) => `/c/${id}/trail`,
};
