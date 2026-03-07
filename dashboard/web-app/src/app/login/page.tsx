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
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-md space-y-6 rounded-2xl border border-slate-700 bg-slate-900/80 p-8">
        <div>
          <h1 className="text-3xl font-bold">Banker Login</h1>
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

        <Link className="block text-sm text-slate-300 underline underline-offset-4" href="/">
          Back Home
        </Link>
      </div>
    </main>
  );
}
