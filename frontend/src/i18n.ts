import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import hi from "./locales/hi.json";
import en from "./locales/en.json";

export type Lang = "hi" | "en";
const STORAGE_KEY = "dhansaathi.lang";

const stored = (() => { try { return typeof localStorage === "undefined" ? null : localStorage.getItem(STORAGE_KEY); } catch { return null; } })();
const initial: Lang = stored === "en" ? "en" : "hi"; // Hindi is the default (brief §9)

i18n.use(initReactI18next).init({
  resources: { hi: { translation: hi }, en: { translation: en } },
  lng: initial,
  fallbackLng: "en",
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
});

const applyLang = (lang: Lang) => {
  if (typeof document === "undefined") return;
  document.documentElement.lang = lang;
  // Devanagari needs ~10% more leading (brief §8).
  document.documentElement.dataset.lang = lang;
};
applyLang(initial);

export function setLang(lang: Lang) {
  i18n.changeLanguage(lang);
  applyLang(lang);
  try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* private mode */ }
}
export const currentLang = (): Lang => (i18n.language === "en" ? "en" : "hi");

export default i18n;
