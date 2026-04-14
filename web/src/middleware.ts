import { NextRequest, NextResponse } from "next/server";

export async function middleware(request: NextRequest) {
  const apiUrl = process.env.API_URL || "http://trader:8000";
  const url = new URL(request.url);
  const destination = `${apiUrl}${url.pathname}${url.search}`;

  // GET/HEAD can use rewrite safely
  if (request.method === "GET" || request.method === "HEAD") {
    return NextResponse.rewrite(new URL(destination));
  }

  // For POST/PUT/DELETE, proxy explicitly to preserve the request body
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    if (!["host", "connection"].includes(key.toLowerCase())) {
      headers[key] = value;
    }
  });

  const body = await request.text();

  try {
    const upstream = await fetch(destination, {
      method: request.method,
      headers,
      body: body || undefined,
    });

    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: Object.fromEntries(upstream.headers.entries()),
    });
  } catch (err) {
    return NextResponse.json(
      { detail: `Backend proxy error: ${err instanceof Error ? err.message : "unknown"}` },
      { status: 502 },
    );
  }
}

export const config = {
  // Match all /api/* EXCEPT /api/chat which has its own Node.js route handler
  matcher: "/api/((?!chat).*)",
};
