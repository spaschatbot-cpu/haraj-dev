/**
 * قراءة الخطأ كما تكتبه الخلفية — T1005.
 *
 * Phase 001 settled the shape of a refusal once, in `apps/core/exceptions.py`:
 *
 *     { "error": { "code": "insufficient_funds",
 *                  "message": "الرصيد المتاح لا يكفي",
 *                  "detail": {} } }
 *
 * `code` is the stable string a client may branch on; `message` is Arabic and
 * already fit to put on a screen; `detail` is always an object, so nothing here
 * has to check whether the key exists.
 *
 * The rule this file exists to hold: **the web never writes its own sentence
 * for a case the backend knows about.** The server refused for a reason, in
 * words chosen by whoever wrote the rule, and a second wording maintained here
 * would drift from it — and the two would disagree in front of a customer, on
 * the same refusal, depending on which channel they happened to open. Only two
 * sentences are written in this file, and both are for the case where there is
 * no server message at all: the network never answered, or what came back was
 * not our envelope.
 */

/** The `detail` map, whatever the backend put in it. Read, never invented. */
export type ErrorDetail = Record<string, unknown>;

export interface ApiErrorBody {
  code: string;
  message: string;
  detail: ErrorDetail;
}

/**
 * A refusal that carries the server's own words to the screen.
 *
 * `message` is not built here and is not translated here. It is the string the
 * backend sent, and `toString()` keeps `code` beside it for the log — the code
 * is what an engineer greps for and the message is what a customer reads, and
 * conflating them loses one of the two audiences.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly detail: ErrorDetail;
  readonly status: number;

  constructor(body: ApiErrorBody, status: number) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.detail = body.detail;
    this.status = status;
  }

  override toString(): string {
    return `${this.code}: ${this.message}`;
  }
}

/** The two codes this layer produces itself, because the server produced none. */
export const CLIENT_CODES = {
  /** The request never reached an answer — offline, DNS, a dropped connection. */
  unreachable: "network_unreachable",
  /** Something answered, and it was not our envelope. A proxy page, an outage. */
  unreadable: "response_unreadable",
} as const;

const CLIENT_MESSAGES: Record<string, string> = {
  [CLIENT_CODES.unreachable]: "تعذّر الاتصال بالخادم. تحقّق من الشبكة وحاول مرة أخرى.",
  [CLIENT_CODES.unreadable]: "وصل ردٌّ غير مفهوم من الخادم. حاول مرة أخرى بعد قليل.",
};

/**
 * True when `value` is the envelope phase 001 defined, with all three fields.
 *
 * Checked rather than assumed: a 502 from a load balancer is an HTML page, and
 * reading `.error.message` off it yields `undefined`, which renders as the word
 * "undefined" on a customer's screen. That is a real v1 screenshot.
 */
function isEnvelope(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error: unknown = (value as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

/**
 * Turn whatever came back into an {@link ApiError}, never into a thrown `undefined`.
 *
 * Every path out of here has a `code` and an Arabic `message`, so a caller can
 * render the result without asking whether the failure was the server refusing
 * or the network vanishing — the distinction is in `code`, for whoever needs it.
 */
export function toApiError(payload: unknown, status: number): ApiError {
  if (isEnvelope(payload)) {
    return new ApiError(
      {
        code: payload.error.code,
        message: payload.error.message,
        detail: payload.error.detail ?? {},
      },
      status,
    );
  }

  const code = status === 0 ? CLIENT_CODES.unreachable : CLIENT_CODES.unreadable;
  return new ApiError({ code, message: CLIENT_MESSAGES[code] ?? "", detail: {} }, status);
}

/**
 * The sentence to show for any thrown value. Never returns an empty string.
 *
 * Used by every error boundary, so a screen that has caught something always has
 * something to say — a blank error state reads as a broken page, and people
 * reload it rather than reporting it.
 */
export function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return CLIENT_MESSAGES[CLIENT_CODES.unreadable] ?? "";
}
