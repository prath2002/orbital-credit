import Link from "next/link";

type DecisionRecordedPageProps = {
  params: Promise<{
    applicationId: string;
  }>;
  searchParams: Promise<{
    zone?: string;
    action?: string;
  }>;
};

export default async function DecisionRecordedPage({ params, searchParams }: DecisionRecordedPageProps) {
  const { applicationId } = await params;
  const query = await searchParams;
  const zone = (query.zone ?? "YELLOW").toUpperCase();
  const action = (query.action ?? "escalate").toLowerCase();

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-6 rounded-xl border border-slate-700 bg-slate-900/70 p-8 text-center">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Decision Recorded</p>
        <h1 className="text-3xl font-bold text-white">Decision Recorded Successfully</h1>
        <p className="text-slate-300">
          Application <span className="font-mono text-white">{applicationId}</span> has been finalized with action{" "}
          <span className="font-semibold text-white">{action}</span> and zone{" "}
          <span className="font-semibold text-white">{zone}</span>.
        </p>

        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-4 text-left text-sm text-slate-300">
          <p>
            <span className="text-slate-400">Application ID:</span> <span className="font-mono">{applicationId}</span>
          </p>
          <p>
            <span className="text-slate-400">Final Action:</span> {action}
          </p>
          <p>
            <span className="text-slate-400">Decision Zone:</span> {zone}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link href="/applications" className="rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:opacity-90">
            Return to Queue
          </Link>
          <Link href={`/applications/${applicationId}`} className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200 hover:bg-slate-800">
            Open Risk Detail
          </Link>
        </div>
      </div>
    </main>
  );
}
