"use client";
import { useEffect, useState } from "react";

const AUTH_COOKIE = "oh_token";

function syncAuthCookie(token: string | null) {
  if (typeof document === "undefined") return;
  if (!token) {
    document.cookie = `${AUTH_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
    return;
  }
  document.cookie = `${AUTH_COOKIE}=${encodeURIComponent(token)}; Path=/; Max-Age=${60 * 60 * 24 * 30}; SameSite=Lax`;
}

export function useIsSignedIn() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(AUTH_COOKIE);
    syncAuthCookie(token);
    setIsSignedIn(!!token);
    setIsLoaded(true);
  }, []);

  return { isSignedIn, isLoaded };
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_COOKIE);
}

export function setAuthToken(token: string) {
  localStorage.setItem(AUTH_COOKIE, token);
  syncAuthCookie(token);
}

export function handleSignOut(redirectUrl: string = "/sign-in") {
  localStorage.removeItem(AUTH_COOKIE);
  syncAuthCookie(null);
  window.location.href = redirectUrl;
}
