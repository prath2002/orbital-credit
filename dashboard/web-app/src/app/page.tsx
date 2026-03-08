import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background-dark px-6">
      <div className="w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 p-8">
        <p className="text-sm uppercase tracking-wider text-slate-400">OC-0601 complete</p>
        <h1 className="mt-2 text-3xl font-bold text-white">Orbital Credit Dashboard Scaffold</h1>
        <p className="mt-3 text-slate-300">
          Next.js app scaffolded with route shells mapped from Stitch exports.
        </p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <Link className="rounded-lg bg-primary px-4 py-3 font-semibold text-white hover:opacity-90" href="/applications/new">
            New Application
          </Link>
          <Link className="rounded-lg bg-primary px-4 py-3 font-semibold text-white hover:opacity-90" href="/login">
            Banker Login
          </Link>
          <Link className="rounded-lg bg-slate-700 px-4 py-3 font-semibold text-white hover:bg-slate-600" href="/applications">
            Loan Application Queue
          </Link>
          <Link
            className="rounded-lg bg-slate-700 px-4 py-3 font-semibold text-white hover:bg-slate-600"
            href="/applications/APP-2024-001"
          >
            Application Risk Analysis
          </Link>
          <Link className="rounded-lg bg-slate-700 px-4 py-3 font-semibold text-white hover:bg-slate-600" href="/system-status">
            System Status Monitoring
          </Link>
        </div>
      </div>
    </main>
  );
}
