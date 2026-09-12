import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Card } from "./Card";
import { StatusChip } from "./Chip";
import type { Light } from "@/copy/mapping";

// Statement first, figure second, traffic light third (brief §6 S1).
export function StatCard({ statement, light, aside }: { statement: ReactNode; light: Light; aside?: ReactNode }) {
  const { t } = useTranslation();
  return (
    <Card tone={light} className="flex flex-col gap-3">
      <p className="text-lg leading-snug">{statement}</p>
      <div className="flex items-center justify-between gap-3">
        <StatusChip light={light}>{t(`light.${light}`)}</StatusChip>
        {aside && <span className="text-sm text-ink-mute tabular">{aside}</span>}
      </div>
    </Card>
  );
}
