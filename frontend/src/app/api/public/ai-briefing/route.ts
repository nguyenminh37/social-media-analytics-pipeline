import { NextRequest, NextResponse } from "next/server";

import { proxyBackendRequest } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const { payload, status } = await proxyBackendRequest(
    "/api/public/ai-briefing",
    request.nextUrl.searchParams,
  );

  return NextResponse.json(payload, { status });
}
