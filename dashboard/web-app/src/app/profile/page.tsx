import Link from "next/link";
import { cookies } from "next/headers";
import { AUTH_BANKER_COOKIE, AUTH_ROLE_COOKIE } from "@/lib/auth";

export default async function ProfilePage() {
  const cookieStore = await cookies();
  const bankerId = cookieStore.get(AUTH_BANKER_COOKIE)?.value ?? "banker_001";
  const role = cookieStore.get(AUTH_ROLE_COOKIE)?.value ?? "banker";

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Profile & Settings</p>
            <h1 className="mt-1 text-3xl font-bold">Banker Profile and Settings</h1>
            <p className="mt-2 text-slate-300">Manage account preferences, notifications, and secure access settings.</p>
          </div>
          <Link className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200 hover:bg-slate-800" href="/applications">
            Back to Queue
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-5 md:col-span-2">
            <h2 className="text-lg font-semibold text-white">Account</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Banker ID</p>
                <p className="mt-1 font-mono text-sm text-white">{bankerId}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Role</p>
                <p className="mt-1 text-sm text-white">{role}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Email</p>
                <p className="mt-1 text-sm text-white">{`${bankerId}@orbital-credit.local`}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Region</p>
                <p className="mt-1 text-sm text-white">India West</p>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <h2 className="text-lg font-semibold text-white">Security</h2>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">
              <li>Two-factor policy: Enforced</li>
              <li>Last login device: Trusted workstation</li>
              <li>Session timeout: 20 minutes</li>
            </ul>
          </section>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <h2 className="text-lg font-semibold text-white">Notification Preferences</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-300">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked readOnly />
                Application escalation alerts
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked readOnly />
                Daily queue summary
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" readOnly />
                Incident bulletin notifications
              </label>
            </div>
          </section>
          <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
            <h2 className="text-lg font-semibold text-white">Working Preferences</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-300">
              <p>Default queue filter: All Zones</p>
              <p>Date format: DD/MM/YYYY</p>
              <p>Timezone: Asia/Kolkata</p>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
