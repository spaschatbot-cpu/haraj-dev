/**
 * الرسالة التي جاء بها الخادم — تُعرض كما هي.
 *
 * One component so every screen shows a refusal the same way, and so no screen
 * has to remember the markup. The text is always the backend's own sentence
 * (T1005); nothing here rewrites, shortens or prefixes one.
 */
export function Notice({ message, tone = "error" }: { message: string; tone?: "error" | "info" }) {
  if (!message) return null;

  const classes =
    tone === "error"
      ? "tone-rose"
      : "tone-navy";

  return (
    <p role="alert" className={`mb-4 rounded-xl border px-4 py-3 text-sm ${classes}`}>
      {message}
    </p>
  );
}
