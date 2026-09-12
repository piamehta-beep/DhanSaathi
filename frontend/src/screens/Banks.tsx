import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useRecommendation, useMatching } from "@/api/queries";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Card, CardSkeleton } from "@/ui";
import { BankCards } from "./BankCards";

// S3 — Compare banks for the current recommendation.
export function Banks() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const rec = useRecommendation(id, i18n.language === "en" ? "en" : "hi");
  const recId = rec.data?.recommendation_id ?? undefined;
  const matching = useMatching(id, recId);

  const error = (rec.isError && !rec.data && rec.error) || (matching.isError && !matching.data && matching.error);
  return (
    <Layout back={paths.suggest(id)} title={t("banks.title")}>
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold">{t("banks.title")}</h1>
        {error ? (
          <ErrorState error={error} onRetry={() => { rec.refetch(); matching.refetch(); }} />
        ) : !matching.data ? (
          <div className="flex flex-col gap-3"><CardSkeleton lines={3} /><CardSkeleton lines={3} /><CardSkeleton lines={3} /></div>
        ) : matching.data.matching_products.length === 0 ? (
          <Card tone="sand"><p lang="en">{matching.data.note ?? matching.data.disclaimer}</p></Card>
        ) : (
          <BankCards products={matching.data.matching_products} />
        )}
      </div>
    </Layout>
  );
}
