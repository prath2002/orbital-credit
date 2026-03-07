import { AUTH_BANKER_COOKIE, AUTH_ROLE_COOKIE } from "@/lib/auth";

export type ActorHeaders = {
  actorId: string;
  actorRole: "banker" | "ops_admin" | "system_service";
};

type CookieReader = {
  get(name: string): { value: string } | undefined;
};

export function resolveActorHeadersFromCookies(cookieStore: CookieReader): ActorHeaders {
  const actorId = cookieStore.get(AUTH_BANKER_COOKIE)?.value?.trim() || "system-default";
  const rawRole = cookieStore.get(AUTH_ROLE_COOKIE)?.value?.trim().toLowerCase();
  const actorRole: ActorHeaders["actorRole"] =
    rawRole === "ops_admin" || rawRole === "system_service" ? rawRole : "banker";
  return { actorId, actorRole };
}

