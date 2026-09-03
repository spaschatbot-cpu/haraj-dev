/**
 * لافتة البيئة — T1006، والمادة ٥-٦.
 *
 * Every environment that is not production says which one it is, in a band
 * nobody can miss. The reason is one specific class of accident: an operator or
 * a tester performing a real, irreversible action — a top-up, a bid — on what
 * they believed was staging, because staging and production look identical.
 *
 * Rendered from a server-read variable, so the banner cannot be switched off by
 * anything in the browser, and its absence in production is the *default* rather
 * than a setting somebody has to remember to flip.
 */
export function EnvironmentBanner({ name }: { name: string }) {
  if (!name || name === "production") return null;

  return (
    <div
      role="status"
      className="w-full bg-amber-200 px-4 py-1 text-center text-sm text-amber-950"
    >
      بيئة <strong>{name}</strong> — ليست الإنتاج. أي عملية هنا ليست حقيقية.
    </div>
  );
}
