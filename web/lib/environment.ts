/**
 * أي بيئة نحن فيها — تُقرأ في مكان واحد.
 *
 * Read on the server and passed down, never read in a client component: an
 * environment name that the browser can see is an environment name the browser
 * can be made to lie about, and the whole value of the banner (T1006) is that
 * it cannot be wrong.
 */
export function environmentName(): string {
  return process.env.ENVIRONMENT_NAME ?? "development";
}
