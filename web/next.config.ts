import type { NextConfig } from "next";

/**
 * Next's configuration, and one setting that is a rule rather than a preference.
 *
 * `typescript.ignoreBuildErrors` is written out at its default (`false`) so that
 * switching it on is a visible edit to this file rather than an absence nobody
 * reviews. T1001's acceptance is that `npm run build` succeeds with a clean
 * `tsc`, and a build that succeeds by ignoring the type checker succeeds at
 * nothing — it is also exactly how a schema change would reach a customer's
 * browser instead of failing the build (T1002 / J2).
 *
 * Lint is not configured here: Next 16 runs no linter during `build`, so
 * `npm run lint` is its own step and CI runs it as one. A setting here that
 * looked like it gated the build would be worse than none.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  typescript: { ignoreBuildErrors: false },

  /**
   * التطوير وحده: `127.0.0.1` أصلٌ مسموح كما `localhost`.
   *
   * خادم التطوير في Next 16 يفحص ترويسة `Origin` على أصوله الخاصة، ويعرف
   * `localhost` ولا يعرف `127.0.0.1` — وهما العنوان نفسه. فمن يفتح الصفحة على
   * الرقم يرى كل أصلٍ من أصول التطوير يُرفض بـ403، **ومنها مصافحة الـWebSocket
   * للتحديث الحيّ**، فيتوقّف عن العمل بلا رسالة تقول لماذا. وقد وقع ذلك فعلاً،
   * وقيس: `Origin: http://localhost:3000` يُجاب بـ200 و`http://127.0.0.1:3000`
   * بـ403 على المسار نفسه.
   *
   * وأثرُه في الإنتاج **صفر**: الإعداد لا يقرأه إلا `next dev`.
   */
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
