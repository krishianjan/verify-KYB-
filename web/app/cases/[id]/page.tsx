import { Suspense } from "react";
import { CaseReport } from "@/components/report/case-report";

async function Resolver({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CaseReport id={id} />;
}

export default function CasePage({ params }: PageProps<"/cases/[id]">) {
  return (
    <div className="mx-auto max-w-3xl px-5 py-12">
      <Suspense fallback={<p className="text-muted-foreground">Loading case…</p>}>
        <Resolver params={params} />
      </Suspense>
    </div>
  );
}
