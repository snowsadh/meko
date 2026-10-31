// Deploy check: verify Railway auto-deploy on push (web).
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PATHS = ["/dashboard", "/onboard", "/setup", "/organization", "/activity", "/storage", "/settings"];
const AUTH_COOKIE = "oh_token";

export default function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Redirect legacy auth routes
  if (pathname === "/login") return NextResponse.redirect(new URL("/sign-in", req.url));
  if (pathname === "/signup") return NextResponse.redirect(new URL("/sign-up", req.url));

  const isProtected = PROTECTED_PATHS.some(
    (protectedPath) => pathname === protectedPath || pathname.startsWith(`${protectedPath}/`),
  );
  const token = req.cookies.get(AUTH_COOKIE)?.value;

  if (isProtected && !token) {
    const url = new URL("/sign-in", req.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
