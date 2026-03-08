import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_BANKER_COOKIE, AUTH_COOKIE, AUTH_ROLE_COOKIE } from "@/lib/auth";

type LoginPageProps = {
  searchParams: Promise<{
    next?: string;
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const resolved = await searchParams;
  const nextPath = resolved.next && resolved.next.startsWith("/") ? resolved.next : "/applications";

  async function loginAction(formData: FormData) {
    "use server";
    const bankerId = String(formData.get("banker_id") ?? "").trim();
    const actorRole = String(formData.get("actor_role") ?? "banker").trim().toLowerCase();
    const next = String(formData.get("next") ?? "/applications");
    if (!bankerId) {
      redirect("/login");
    }

    const cookieStore = await cookies();
    cookieStore.set(AUTH_COOKIE, "1", { httpOnly: true, sameSite: "lax", path: "/" });
    cookieStore.set(AUTH_BANKER_COOKIE, bankerId, { httpOnly: true, sameSite: "lax", path: "/" });
    cookieStore.set(AUTH_ROLE_COOKIE, actorRole, { httpOnly: true, sameSite: "lax", path: "/" });

    const destination = next.startsWith("/") ? next : "/applications";
    if (destination === "/applications") {
      redirect(`/applications?banker_id=${encodeURIComponent(bankerId)}`);
    }
    redirect(destination);
  }

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100 lg:p-0">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/80 lg:grid-cols-2">
        <div className="space-y-6 p-8 lg:p-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-bold uppercase tracking-wide text-emerald-300">
            System Status: Operational
          </div>
          <div>
            <h1 className="text-3xl font-bold">Secure Banker Login</h1>
            <p className="mt-2 text-slate-300">Access the Orbital-Credit loan processing system.</p>
          </div>

          <form action={loginAction} className="space-y-4">
            <input type="hidden" name="next" value={nextPath} />
            <label className="block text-sm text-slate-300" htmlFor="banker_id">
              Banker ID
            </label>
            <input
              id="banker_id"
              name="banker_id"
              required
              placeholder="Enter your banker ID"
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white outline-none ring-primary focus:ring-2"
            />
            <label className="block text-sm text-slate-300" htmlFor="actor_role">
              Role
            </label>
            <select
              id="actor_role"
              name="actor_role"
              defaultValue="banker"
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white outline-none ring-primary focus:ring-2"
            >
              <option value="banker">banker</option>
              <option value="ops_admin">ops_admin</option>
              <option value="system_service">system_service</option>
            </select>
            <button type="submit" className="w-full rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:opacity-90">
              Sign In to Dashboard
            </button>
          </form>

          <div className="space-y-2 text-xs text-slate-400">
            <p>Enterprise controls enabled for banker, ops-admin, and service roles.</p>
            <p>Monitoring: active | Session policy: secure cookie</p>
          </div>

          <Link className="block text-sm text-slate-300 underline underline-offset-4" href="/">
            Back Home
          </Link>
        </div>
        <div className="hidden bg-[radial-gradient(circle_at_20%_20%,rgba(19,127,236,0.35),transparent_40%),radial-gradient(circle_at_80%_70%,rgba(34,197,94,0.25),transparent_45%),linear-gradient(135deg,#0f172a,#111827)] p-12 lg:block">
          <h2 className="max-w-sm text-4xl font-bold leading-tight text-white">Satellite Intelligence for Responsible Credit Decisions.</h2>
          <p className="mt-4 max-w-md text-slate-200">
            Use real-time geospatial, debt, and social signals to approve, escalate, or reject cases with full explainability.
          </p>
        </div>
      </div>
    </main>
  );
}
