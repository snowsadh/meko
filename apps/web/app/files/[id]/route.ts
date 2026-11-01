import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return new NextResponse("File not found", { status: 404 });
  const token = (await cookies()).get("oh_token")?.value;
  if (!token) {
    const signIn = new URL("/sign-in", request.url);
    signIn.searchParams.set("next", `/files/${id}`);
    return NextResponse.redirect(signIn);
  }
  const base = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const result = await fetch(`${base}/api/agent/files/${id}`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
  });
  if (!result.ok) return new NextResponse("File unavailable. Sign in to its company account.", { status: result.status });
  const headers = new Headers();
  for (const name of ["content-type", "content-disposition", "cache-control", "x-content-type-options", "content-security-policy", "x-content-sha256"]) {
    const value = result.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(result.body, { headers });
}
