"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { RiskScoreResponse } from "@/lib/types";

type DecisionActionPanelProps = {
  applicationId: string;
  risk: RiskScoreResponse;
  suggestedAction?: "approve" | "reject" | "escalate";
};

type ActionType = "APPROVE" | "REJECT" | "ESCALATE";

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function DecisionActionPanel({ applicationId, risk, suggestedAction }: DecisionActionPanelProps) {
  const router = useRouter();
  const [modalOpen, setModalOpen] = useState(false);
  const initialAction: ActionType =
    suggestedAction === "approve" ? "APPROVE" : suggestedAction === "reject" ? "REJECT" : "ESCALATE";
  const [actionType, setActionType] = useState<ActionType>(initialAction);
  const [actorId, setActorId] = useState("banker_ui");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const decisionDefaults = useMemo(() => {
    const satelliteScore = risk.satellite.score ?? 0;
    const debtScore = risk.debt.score ?? null;
    const socialScore = risk.social.score ?? null;
    const satelliteDataQuality = clamp(risk.satellite.quality ?? 0.8, 0, 1);
    const debtToIncomeRatio = risk.debt.debt_to_income_ratio ?? null;
    const debtStatus = risk.debt.status ?? null;
    const socialVerifiedReferences = risk.social.verified_references ?? null;
    const noCrop = (risk.satellite.flags ?? []).includes("no_crop_history");
    const fireDetected = (risk.satellite.flags ?? []).includes("fire_detected");

    return {
      satellite_score: satelliteScore,
      debt_score: debtScore,
      social_score: socialScore,
      satellite_data_quality: satelliteDataQuality,
      debt_to_income_ratio: debtToIncomeRatio,
      debt_status: debtStatus,
      social_verified_references: socialVerifiedReferences,
      satellite_no_crop_history: noCrop,
      satellite_fire_detected: fireDetected,
      identity_verification_failed: false,
    };
  }, [risk]);

  const canSubmit = risk.satellite.score !== null;

  async function submitDecision() {
    if (!canSubmit) {
      setError("Satellite score is still pending. Decision cannot be finalized yet.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    const rationale =
      actionType === "APPROVE"
        ? `Approved by banker: ${notes || "No additional notes"}`
        : actionType === "REJECT"
          ? `Rejected by banker: ${notes || "No additional notes"}`
          : `Escalated for manual review: ${notes || "No additional notes"}`;

    const payload = {
      ...decisionDefaults,
      manual_action:
        actionType === "APPROVE" ? "approve" : actionType === "REJECT" ? "reject" : "escalate",
      rationale_override: rationale,
      actor_id: actorId || "banker_ui",
    };

    try {
      const response = await fetch(`/api/decisions/${applicationId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.error ?? "Decision request failed");
      }
      setSuccess(`Decision submitted: ${body.traffic_light_status}`);
      setModalOpen(false);
      const zone = encodeURIComponent(body.traffic_light_status ?? "YELLOW");
      const action = encodeURIComponent(actionType.toLowerCase());
      router.push(`/applications/${applicationId}/decision-recorded?zone=${zone}&action=${action}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Decision request failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <h2 className="text-lg font-semibold text-white">Decision Action</h2>
      <p className="mt-1 text-sm text-slate-300">Finalize banker action with confirmation modal (OC-0604).</p>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => {
            setActionType("APPROVE");
            setModalOpen(true);
          }}
          className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500"
        >
          Approve
        </button>
        <button
          type="button"
          onClick={() => {
            setActionType("ESCALATE");
            setModalOpen(true);
          }}
          className="rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white hover:bg-amber-500"
        >
          Escalate
        </button>
        <button
          type="button"
          onClick={() => {
            setActionType("REJECT");
            setModalOpen(true);
          }}
          className="rounded-lg bg-rose-600 px-4 py-2 font-semibold text-white hover:bg-rose-500"
        >
          Reject
        </button>
      </div>

      {!canSubmit ? <p className="mt-3 text-sm text-amber-300">Decision is disabled until risk scores are available.</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      {success ? <p className="mt-3 text-sm text-emerald-300">{success}</p> : null}

      {modalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-5">
            <h3 className="text-xl font-semibold text-white">Confirm {actionType}</h3>
            <p className="mt-1 text-sm text-slate-300">Application: {applicationId}</p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="actor_id">
                  Actor ID
                </label>
                <input
                  id="actor_id"
                  value={actorId}
                  onChange={(event) => setActorId(event.target.value)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="notes">
                  Notes
                </label>
                <textarea
                  id="notes"
                  rows={3}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white"
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={submitDecision}
                className="rounded-lg bg-primary px-4 py-2 font-semibold text-white disabled:opacity-60"
              >
                {submitting ? "Submitting..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
