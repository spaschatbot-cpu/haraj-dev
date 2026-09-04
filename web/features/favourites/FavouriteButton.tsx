/**
 * زرّ المفضّلة — نموذج، لا زرٌّ يبدّل حالةً في المتصفح.
 *
 * Works with scripting off like every other write in this app, and the state it
 * shows is the state the server holds: `marked` comes from the page's own read,
 * so a filled heart means a stored mark and nothing else.
 */

import { addFavourite, removeFavourite } from "@/features/favourites/actions";

export function FavouriteButton({
  vehicleId,
  marked,
  back,
}: {
  vehicleId: number;
  marked: boolean;
  /** The page to refresh after — where the customer actually is. */
  back: string;
}) {
  return (
    <form action={marked ? removeFavourite : addFavourite}>
      <input type="hidden" name="vehicle_id" value={vehicleId} />
      <input type="hidden" name="back" value={back} />
      <button
        type="submit"
        aria-pressed={marked}
        className="rounded border border-neutral-500 px-3 py-1.5 text-sm hover:bg-neutral-50"
      >
        {marked ? "★ في المفضّلة" : "☆ أضف للمفضّلة"}
      </button>
    </form>
  );
}
