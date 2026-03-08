import { NextResponse } from "next/server";
import { AUTH_BANKER_COOKIE, AUTH_COOKIE, AUTH_ROLE_COOKIE } from "@/lib/auth";

export async function POST(request: Request) {
  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  response.cookies.set(AUTH_COOKIE, "", { path: "/", maxAge: 0 });
  response.cookies.set(AUTH_BANKER_COOKIE, "", { path: "/", maxAge: 0 });
  response.cookies.set(AUTH_ROLE_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}
