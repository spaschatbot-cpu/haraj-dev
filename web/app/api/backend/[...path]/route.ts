/**
 * الممرّ الشفّاف إلى الخلفية — T1004، وحارس القاعدة الأولى في الفيز 011.
 *
 * The browser cannot read the session cookie (it is `HttpOnly`) and must not
 * hold the token in any other form, so it cannot call the backend itself. It
 * calls this instead, and this attaches the token and forwards.
 *
 * **The path is forwarded unchanged, and that is the design.** Rule 1 of spec
 * 011 is *لا نقطة API خاصة بالويب*, and a proxy that maps, renames, merges or
 * invents paths is exactly how a web-only endpoint appears — not by anybody
 * deciding to add one, but by a handler growing a convenient special case for
 * one screen. Here there is nowhere to put such a case: whatever `/api/backend/x`
 * is asked for becomes `/x` at the backend, and if the backend does not have it,
 * the browser gets the backend's own 404.
 *
 * It also does not read or interpret the body. A proxy that parses responses
 * ends up "helpfully" reshaping one, and then the web is looking at a different
 * object than the app is (rule 3: no business logic in the web).
 */

import { type NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

import { backendUrl } from "@/lib/api";
import { authHeader } from "@/lib/session";

//: Hop-by-hop and length headers that belong to *this* connection, not to the
//: forwarded message. Passing `host` on sends the browser's idea of the host to
//: the backend, and passing `content-length` on after any re-encoding produces a
//: request that hangs waiting for bytes that never come.
const STRIPPED = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "accept-encoding",
]);

function forwardedHeaders(request: NextRequest, auth: Record<string, string>): Headers {
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!STRIPPED.has(key.toLowerCase())) headers.set(key, value);
  });
  // Set last, so a browser cannot supply its own Authorization and have it win.
  // The only token that reaches the backend is the one in the HttpOnly cookie.
  for (const [key, value] of Object.entries(auth)) headers.set(key, value);
  return headers;
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  const store = await cookies();

  const target = `${backendUrl()}/${path.join("/")}${request.nextUrl.search}`;
  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers: forwardedHeaders(request, authHeader(store)),
      body,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    // The backend did not answer. Answered in the envelope phase 001 defined,
    // so the client's error handling has one shape to read and not two.
    return NextResponse.json(
      {
        error: {
          code: "network_unreachable",
          message: "تعذّر الاتصال بالخادم. حاول مرة أخرى بعد قليل.",
          detail: {},
        },
      },
      { status: 502 },
    );
  }

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
  });
  upstream.headers.forEach((value, key) => {
    // `set-cookie` is dropped on purpose: the backend does not set our session,
    // this app does (`lib/session.ts`), and a cookie arriving from upstream and
    // being passed through would be a second, unmanaged place a token could
    // land in the browser.
    if (!STRIPPED.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") {
      response.headers.set(key, value);
    }
  });
  return response;
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const PUT = forward;
export const DELETE = forward;

//: Node, not the edge runtime: the backend is reached over the private network
//: in production, and an edge function does not sit on it.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
