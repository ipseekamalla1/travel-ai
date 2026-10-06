import { NextResponse, type NextRequest } from "next/server";

/**
 * Optimistic routing only: checks whether a session cookie *exists*, never whether it is valid.
 * The API authorizes every request; `RequireAuth` handles cookies the API rejects.
 */
const SESSION_COOKIE = "atu_session";
const AUTH_PAGES = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const isAuthPage = AUTH_PAGES.includes(pathname);

  if (isAuthPage) {
    return hasSession
      ? NextResponse.redirect(new URL("/universe", request.url))
      : NextResponse.next();
  }

  if (!hasSession) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  // Protected app areas (add each as its phase ships) + the auth pages.
  matcher: ["/universe/:path*", "/login", "/register"],
};
