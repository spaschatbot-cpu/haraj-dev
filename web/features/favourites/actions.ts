"use server";

/**
 * المفضّلة من الويب — T1013.
 *
 * Two actions and no state. The mark lives in the database (see
 * `apps/auctions/favourites.py` for why), so this layer's whole job is to say
 * which car and let the server remember.
 *
 * `revalidatePath` rather than a client-side toggle: the heart's filled or empty
 * state is read from the server on the next render, so what the customer sees is
 * what is stored. An optimistic toggle would show a filled heart for a request
 * that failed — and the customer would find the car missing from their list
 * later, with no idea when it went.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { ApiError, api, messageOf, request } from "@/lib/api";
import { setFlash } from "@/lib/flash";
import { authHeader } from "@/lib/session";

async function toggle(vehicleId: number, on: boolean, back: string): Promise<void> {
  const headers = await authHeader(await cookies());

  try {
    if (on) {
      await request(() =>
        api.PUT("/api/v1/favourites/{id}/", {
          params: { path: { id: vehicleId } },
          headers,
        }),
      );
    } else {
      await request(() =>
        api.DELETE("/api/v1/favourites/{id}/", {
          params: { path: { id: vehicleId } },
          headers,
        }),
      );
    }
  } catch (error) {
    const store = await cookies();
    setFlash(store, {
      code: error instanceof ApiError ? error.code : "",
      message: messageOf(error),
    });
  }

  // Both the page the customer is on and the favourites list: marking from a
  // vehicle page must not leave a stale «مفضّلتي» behind it.
  revalidatePath(back);
  revalidatePath("/favourites");
}

export async function addFavourite(form: FormData): Promise<void> {
  await toggle(
    Number(form.get("vehicle_id")),
    true,
    String(form.get("back") ?? "/favourites"),
  );
}

export async function removeFavourite(form: FormData): Promise<void> {
  await toggle(
    Number(form.get("vehicle_id")),
    false,
    String(form.get("back") ?? "/favourites"),
  );
}
