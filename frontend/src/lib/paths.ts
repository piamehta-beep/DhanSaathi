export const paths = {
  welcome: "/",
  onboarding: "/start",
  home: (id: string) => `/c/${id}`,
  suggest: (id: string) => `/c/${id}/suggest`,
  banks: (id: string) => `/c/${id}/banks`,
  ask: (id: string) => `/c/${id}/ask`,
  why: (id: string) => `/c/${id}/why`,
  data: (id: string, scope?: string) => `/c/${id}/data${scope ? `?scope=${scope}` : ""}`,
};
