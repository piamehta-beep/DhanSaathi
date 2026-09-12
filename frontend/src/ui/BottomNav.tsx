import { NavLink, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Home, Sparkles, Search, TrendingUp, Receipt } from "lucide-react";
import { paths } from "@/lib/paths";

// Five labelled tabs for the customer-scoped screens. Fixed to the bottom on
// phones (thumb reach), a row under the header on wider screens.
export function BottomNav() {
  const { t } = useTranslation();
  const { id } = useParams();
  if (!id) return null;
  const items = [
    { to: paths.home(id), label: t("tab.home"), Icon: Home, end: true },
    { to: paths.suggest(id), label: t("tab.suggest"), Icon: Sparkles },
    { to: paths.ask(id), label: t("tab.ask"), Icon: Search },
    { to: paths.future(id), label: t("tab.future"), Icon: TrendingUp },
    { to: paths.money(id), label: t("tab.money"), Icon: Receipt },
  ];
  return (
    <nav aria-label={t("nav.home")} className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/95 backdrop-blur safe-bottom sm:static sm:border-t-0 sm:border-b sm:bg-paper">
      <ul className="mx-auto grid max-w-3xl grid-cols-5 sm:flex sm:gap-1 sm:px-6">
        {items.map(({ to, label, Icon, end }) => (
          <li key={to} className="sm:flex-none">
            <NavLink to={to} end={end}
              className={({ isActive }) =>
                "flex min-h-[56px] flex-col items-center justify-center gap-0.5 px-1 text-sm font-semibold sm:min-h-touch sm:flex-row sm:gap-2 sm:rounded-none sm:border-b-2 sm:px-3 " +
                (isActive ? "text-accent-strong sm:border-accent" : "text-ink-mute hover:text-ink sm:border-transparent")}>
              <Icon size={22} aria-hidden /> <span>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
