import { useTranslation } from "react-i18next";
import { Receipt, Calculator, Brain, Scale, ShieldCheck, Landmark, ScrollText, ArrowRight } from "lucide-react";
import { useHealth } from "@/api/queries";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { Card, LinkButton } from "@/ui";

// Judge-facing: the pipeline in seven steps, what the system refuses to do,
// and the backend's validation results (from its test suite, seed 42).
export function About() {
  const { t } = useTranslation();
  const health = useHealth();
  const steps = [
    { k: "step1", Icon: Receipt, tone: "sand" }, { k: "step2", Icon: Calculator, tone: "sand" }, { k: "step3", Icon: Brain, tone: "sand" },
    { k: "step4", Icon: Scale, tone: "sand" }, { k: "step5", Icon: ShieldCheck, tone: "accent" }, { k: "step6", Icon: Landmark, tone: "sand" }, { k: "step7", Icon: ScrollText, tone: "sand" },
  ] as const;
  const results = ["cindex", "sim", "anom", "fpr", "violations", "noaction", "distressed", "fair"];
  return (
    <Layout back={paths.welcome} title={t("about.title")}>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-bold">{t("about.title")}</h1>
          <p className="text-ink-soft">{t("about.lead")}</p>
        </div>

        <ol className="relative flex flex-col gap-3 border-l-2 border-line pl-6">
          {steps.map(({ k, Icon, tone }) => (
            <li key={k} className="relative">
              <span aria-hidden className={"absolute -left-[31px] top-3 inline-flex h-8 w-8 items-center justify-center rounded-full " + (tone === "accent" ? "bg-accent text-white" : "bg-sand text-ink-soft")}><Icon size={18} /></span>
              <Card tone={tone} className="flex flex-col gap-1">
                <h2 className="font-bold">{t(`about.${k}.title`)}</h2>
                <p className="text-ink-soft">{t(`about.${k}.body`)}</p>
              </Card>
            </li>
          ))}
        </ol>

        <section className="flex flex-col gap-3" aria-labelledby="honest-h">
          <h2 id="honest-h" className="text-lg font-bold">{t("about.honest.title")}</h2>
          <Card>
            <ul className="flex list-disc flex-col gap-2 pl-5">
              {[1, 2, 3, 4].map((n) => <li key={n}>{t(`about.honest.${n}`)}</li>)}
            </ul>
          </Card>
        </section>

        <section className="flex flex-col gap-3" aria-labelledby="res-h">
          <div>
            <h2 id="res-h" className="text-lg font-bold">{t("about.results.title")}</h2>
            <p className="text-sm text-ink-soft">{t("about.results.lead")}</p>
          </div>
          <Card>
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              {results.map((r) => (
                <div key={r} className="flex justify-between gap-3 border-b border-line pb-2 text-sm sm:text-base">
                  <dt className="text-ink-soft">{t(`about.r.${r}`)}</dt>
                  <dd className="shrink-0 font-semibold tabular">{t(`about.r.${r}V`)}</dd>
                </div>
              ))}
            </dl>
            {health.data && <p className="mt-3 text-sm text-ink-mute">{t("about.version", { v: health.data.model_version })}</p>}
          </Card>
        </section>

        <LinkButton to={paths.welcome} variant="primary" icon={<ArrowRight size={22} aria-hidden />}>{t("about.back")}</LinkButton>
      </div>
    </Layout>
  );
}
