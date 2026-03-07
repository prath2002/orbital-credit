import {
  BankerApplicationsResponse,
  DecisionRequestPayload,
  DecisionResponse,
  RiskScoreResponse,
} from "@/lib/types";
import { ActorHeaders } from "@/lib/actor";

const BASE_URL = process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000";

type ApiResult<T> = {
  data: T | null;
  error: string | null;
};

type FetchOptions = {
  init?: RequestInit;
  actorHeaders?: ActorHeaders;
};

async function fetchJson<T>(path: string, options?: FetchOptions): Promise<ApiResult<T>> {
  try {
    const headers = new Headers(options?.init?.headers);
    headers.set("Content-Type", "application/json");
    if (options?.actorHeaders) {
      headers.set("X-Actor-Id", options.actorHeaders.actorId);
      headers.set("X-Actor-Role", options.actorHeaders.actorRole);
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      ...(options?.init ?? {}),
      headers,
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      return { data: null, error: `HTTP ${response.status}: ${errorText || "Request failed"}` };
    }

    return { data: (await response.json()) as T, error: null };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : "Network error" };
  }
}

export async function getBankerApplications(
  bankerId: string,
  actorHeaders?: ActorHeaders,
): Promise<ApiResult<BankerApplicationsResponse>> {
  return fetchJson<BankerApplicationsResponse>(`/api/v1/applications/${encodeURIComponent(bankerId)}`, {
    actorHeaders,
  });
}

export async function getRiskScore(
  applicationId: string,
  actorHeaders?: ActorHeaders,
): Promise<ApiResult<RiskScoreResponse>> {
  return fetchJson<RiskScoreResponse>(`/api/v1/risk-score/${encodeURIComponent(applicationId)}`, {
    actorHeaders,
  });
}

export async function postDecision(
  applicationId: string,
  payload: DecisionRequestPayload,
  actorHeaders?: ActorHeaders,
): Promise<ApiResult<DecisionResponse>> {
  return fetchJson<DecisionResponse>(`/api/v1/decisions/${encodeURIComponent(applicationId)}`, {
    actorHeaders,
    init: {
      method: "POST",
      body: JSON.stringify(payload),
    },
  });
}

export async function getMetrics(actorHeaders?: ActorHeaders): Promise<ApiResult<string>> {
  try {
    const response = await fetch(`${BASE_URL}/metrics`, {
      method: "GET",
      headers: actorHeaders
        ? {
            "X-Actor-Id": actorHeaders.actorId,
            "X-Actor-Role": actorHeaders.actorRole,
          }
        : undefined,
      cache: "no-store",
    });
    if (!response.ok) {
      return { data: null, error: `HTTP ${response.status}: ${await response.text()}` };
    }
    return { data: await response.text(), error: null };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : "Network error" };
  }
}
