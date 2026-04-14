import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

// 10 minute timeout — chat blocks on the Ollama lock if another agent is running
const TIMEOUT_MS = 600_000;

export async function POST(request: NextRequest) {
  const apiUrl = process.env.API_URL || "http://trader:8000";
  const body = await request.text();

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const upstream = await fetch(`${apiUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: controller.signal,
    });

    const data = await upstream.text();
    return new NextResponse(data, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    if (controller.signal.aborted) {
      return NextResponse.json(
        { detail: "Request timed out — the LLM may be busy with another task. Try again in a minute." },
        { status: 504 },
      );
    }
    return NextResponse.json(
      { detail: `Backend error: ${err instanceof Error ? err.message : "unknown"}` },
      { status: 502 },
    );
  } finally {
    clearTimeout(timer);
  }
}
