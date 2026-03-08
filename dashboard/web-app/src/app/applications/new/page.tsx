import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { analyzeFarm } from "@/lib/backend";
import { AUTH_BANKER_COOKIE } from "@/lib/auth";
import { resolveActorHeadersFromCookies } from "@/lib/actor";

type NewApplicationPageProps = {
  searchParams: Promise<{
    error?: string;
  }>;
};

export default async function NewApplicationPage({ searchParams }: NewApplicationPageProps) {
  const params = await searchParams;
  const cookieStore = await cookies();
  const actorHeaders = resolveActorHeadersFromCookies(cookieStore);
  const bankerFromCookie = cookieStore.get(AUTH_BANKER_COOKIE)?.value ?? "";

  async function createApplicationAction(formData: FormData) {
    "use server";
    const cookieStoreForAction = await cookies();
    const actorHeadersForAction = resolveActorHeadersFromCookies(cookieStoreForAction);
    const farmerMobile = String(formData.get("farmer_mobile") ?? "").trim();
    const bankerId = String(formData.get("banker_id") ?? "").trim();
    const loanAmount = Number(formData.get("loan_amount") ?? 0);
    const latitude = Number(formData.get("latitude") ?? 0);
    const longitude = Number(formData.get("longitude") ?? 0);
    const reference1 = String(formData.get("reference_1") ?? "").trim();
    const reference2 = String(formData.get("reference_2") ?? "").trim();
    const idempotencyKey = `ui-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

    const result = await analyzeFarm(
      {
        gps_coordinates: { latitude, longitude },
        farmer_mobile: farmerMobile,
        loan_amount: loanAmount,
        references: [reference1, reference2],
        banker_id: bankerId || actorHeadersForAction.actorId,
      },
      actorHeadersForAction,
      idempotencyKey,
    );

    if (result.error || !result.data) {
      redirect(`/applications/new?error=${encodeURIComponent(result.error ?? "Failed to create application")}`);
    }
    redirect(`/applications/${result.data.application_id}`);
  }

  return (
    <main className="min-h-screen bg-background-dark p-6 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">New Application</p>
            <h1 className="mt-1 text-3xl font-bold">Analyze Farm Application</h1>
            <p className="mt-2 text-slate-300">Submit a new farmer case for satellite, debt, and social risk analysis.</p>
          </div>
          <Link className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200" href="/applications">
            Back to Queue
          </Link>
        </div>

        {params.error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            Failed to submit application: {params.error}
          </div>
        ) : null}

        <form action={createApplicationAction} className="grid gap-4 rounded-xl border border-slate-700 bg-slate-900/70 p-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-slate-300" htmlFor="banker_id">
              Banker ID
            </label>
            <input
              id="banker_id"
              name="banker_id"
              defaultValue={bankerFromCookie || actorHeaders.actorId}
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="farmer_mobile">
              Farmer Mobile (+91XXXXXXXXXX)
            </label>
            <input
              id="farmer_mobile"
              name="farmer_mobile"
              placeholder="+919876543210"
              pattern="^\+91\d{10}$"
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="loan_amount">
              Loan Amount (INR)
            </label>
            <input
              id="loan_amount"
              name="loan_amount"
              type="number"
              min={20000}
              max={50000}
              defaultValue={30000}
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="latitude">
              Latitude
            </label>
            <input
              id="latitude"
              name="latitude"
              type="number"
              step="0.000001"
              defaultValue={19.076}
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="longitude">
              Longitude
            </label>
            <input
              id="longitude"
              name="longitude"
              type="number"
              step="0.000001"
              defaultValue={72.8777}
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="reference_1">
              Reference Mobile 1
            </label>
            <input
              id="reference_1"
              name="reference_1"
              placeholder="+919900001111"
              pattern="^\+91\d{10}$"
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="reference_2">
              Reference Mobile 2
            </label>
            <input
              id="reference_2"
              name="reference_2"
              placeholder="+919900002222"
              pattern="^\+91\d{10}$"
              required
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
            />
          </div>

          <div className="sm:col-span-2">
            <button type="submit" className="w-full rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:opacity-90">
              Submit for Analysis
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
