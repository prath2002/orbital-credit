import { NextRequest, NextResponse } from "next/server";
import { postDecision } from "@/lib/backend";
import { resolveActorHeadersFromCookies } from "@/lib/actor";
import { DecisionRequestPayload } from "@/lib/types";

type Context = {
  params: Promise<{
    applicationId: string;
  }>;
};

export async function POST(request: NextRequest, { params }: Context) {
  const { applicationId } = await params;
  const payload = (await request.json()) as DecisionRequestPayload;
  const actorHeaders = resolveActorHeadersFromCookies(request.cookies);
  const result = await postDecision(applicationId, payload, actorHeaders);

  if (result.error || !result.data) {
    return NextResponse.json({ error: result.error ?? "Failed to finalize decision" }, { status: 400 });
  }

  return NextResponse.json(result.data);
}
