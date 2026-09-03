/**
 * أنواع حرّاس `ops/checks` التي تستوردها الاختبارات.
 *
 * The guards are plain node scripts, run by CI as executables and imported by
 * one test each so that a guard nothing executes cannot rot unnoticed. They have
 * no types of their own and `noImplicitAny` is on (T1001), so the shape they
 * export is declared here rather than switched off with an `any` at the call
 * site — the signature is small, and writing it down is what keeps the test
 * honest if the guard's return type ever changes.
 */
declare module "*/web_tokens_are_httponly.mjs" {
  /** Every offending `path:line: reason`, or an empty array when clean. */
  export function violations(root?: string): Promise<string[]>;
}
