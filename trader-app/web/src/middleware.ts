import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const apiUrl = process.env.API_URL || "http://trader:8000";
  const url = new URL(request.url);
  const destination = `${apiUrl}${url.pathname}${url.search}`;

  return NextResponse.rewrite(new URL(destination));
}

export const config = {
  matcher: "/api/:path*",
};
