/**
 * T1005 — رسالة الخادم تصل كما هي، ولا تُكتب رسالة محلية لحالة تعرفها الخلفية.
 *
 * The criterion is *«اختبار لكل رمز خطأ شائع يؤكد ظهور رسالة الخادم لا رسالة
 * محلية»*, so the codes below are the real ones the backend raises, with the
 * sentences it actually sends. The point of each case is the same and is worth
 * stating once: the person who wrote the rule wrote the refusal, and a second
 * wording maintained here would drift from it — until the app and the web told
 * one customer two different things about one refusal.
 *
 * The two tests at the end are the other half: when there is no server message,
 * there must still be a sentence. A blank error state reads as a broken page,
 * and people reload it instead of reporting it.
 */

import { describe, expect, it } from "vitest";

import { ApiError, CLIENT_CODES, messageOf, toApiError } from "@/lib/api/errors";

/** Envelopes exactly as `apps/core/exceptions.py` builds them. */
const FROM_BACKEND = [
  {
    code: "insufficient_funds",
    message: "الرصيد المتاح لا يكفي",
    detail: { available: "2000.00", required: "10000.00" },
    status: 409,
  },
  {
    code: "unpaid_dues",
    message: "عليك مستحقات غير مسدَّدة، سدّدها قبل المزايدة.",
    detail: { outstanding: "8000.00" },
    status: 409,
  },
  {
    code: "otp_incorrect",
    message: "الرمز غير صحيح.",
    detail: {},
    status: 400,
  },
  {
    code: "not_found",
    message: "غير موجود.",
    detail: {},
    status: 404,
  },
];

describe("the server's own sentence reaches the screen", () => {
  it.each(FROM_BACKEND)("$code", ({ code, message, detail, status }) => {
    const error = toApiError({ error: { code, message, detail } }, status);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(message);
    expect(error.code).toBe(code);
    expect(error.status).toBe(status);
    expect(error.detail).toEqual(detail);
  });

  it("keeps the code beside the message for the log, and apart from it", () => {
    // Two audiences: an engineer greps the code, a customer reads the message.
    // A single string that serves both serves neither.
    const error = toApiError(
      { error: { code: "insufficient_funds", message: "الرصيد المتاح لا يكفي", detail: {} } },
      409,
    );

    expect(String(error)).toBe("insufficient_funds: الرصيد المتاح لا يكفي");
    expect(messageOf(error)).toBe("الرصيد المتاح لا يكفي");
  });

  it("carries `detail` through untouched, including the amounts as strings", () => {
    // Article 3-2 reaches here too: an amount is the digits the server sent.
    // Anything that parsed them into a number on the way would have to render
    // them back, and `0.1 + 0.2` is not `0.3` in JavaScript either.
    const error = toApiError(
      {
        error: {
          code: "insufficient_funds",
          message: "الرصيد المتاح لا يكفي",
          detail: { available: "2000.00" },
        },
      },
      409,
    );

    expect(error.detail.available).toBe("2000.00");
    expect(typeof error.detail.available).toBe("string");
  });
});

describe("when there is no server message", () => {
  it("says the network failed, and says which kind of failure that is", () => {
    const error = toApiError(undefined, 0);

    expect(error.code).toBe(CLIENT_CODES.unreachable);
    expect(error.message).toContain("تعذّر الاتصال");
  });

  it("does not read `undefined` off a body that is not our envelope", () => {
    // A 502 from a load balancer is an HTML page. Reading `.error.message` off
    // it yields `undefined`, which renders as the word "undefined" on a
    // customer's screen — a real v1 screenshot.
    const error = toApiError("<html>502 Bad Gateway</html>", 502);

    expect(error.code).toBe(CLIENT_CODES.unreadable);
    expect(error.message).not.toContain("undefined");
    expect(error.message.length).toBeGreaterThan(0);
  });

  it("refuses a half-shaped envelope rather than trusting it", () => {
    const error = toApiError({ error: { code: "oops" } }, 500);

    expect(error.code).toBe(CLIENT_CODES.unreadable);
  });

  it("always has something to say, whatever was thrown", () => {
    for (const thrown of [new Error("boom"), "boom", null, undefined, 42]) {
      expect(messageOf(thrown).length).toBeGreaterThan(0);
    }
  });
});
