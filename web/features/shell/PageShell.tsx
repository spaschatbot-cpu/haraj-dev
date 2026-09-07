/**
 * إطار الصفحات العامة — رأسٌ وذيلٌ وحدود عرض، في مكان واحد.
 *
 * Not a layout file, because the signed-in shell will differ and a single
 * layout that branches on the session is a layout that renders the wrong header
 * on the one page somebody forgot to pass the flag to.
 *
 * الرأس ثابتٌ أعلى الشاشة — T1032
 * ================================
 * `sticky` لا `fixed`: التنقّل يبقى في المتناول وهو يمرّر شبكةً من أربعمئة
 * سيارة، و`sticky` يحجز مكانه في التدفّق فلا يحتاج حشوةً علوية تُحسب بيدٍ في
 * كل صفحة وتُنسى في واحدة.
 *
 * وما ليس في الرأس، وسببه
 * =======================
 * التصميم المرجعيّ يضع فيه **جرس إشعارات** و**رصيد المحفظة**. وليس أيّهما
 * هنا:
 *
 * * **الجرس** لا مصدر له — لا نقطة إشعاراتٍ في العقد للويب، وجرسٌ لا يرنّ
 *   أبداً أسوأ من لا جرس؛
 * * **الرصيد** له مصدر (`GET /api/v1/wallet/`) لكنه **طلبٌ إضافيّ في كل
 *   صفحة** — بما فيها الصفحات التي لا علاقة لها بالمال — مقابل رقمٍ لصفحته
 *   شاشةٌ كاملة. يُضاف يوم يُقرَّر أنه يستحقّ ذلك الطلب، لا قبله.
 */

import Link from "next/link";

//: المسارات كما هي في `app/`. مصفوفةٌ لا ستّة أسطر متكرّرة: صفٌّ يُنسى في
//: النسخة السادسة هو رابطٌ بصيغةٍ مختلفة عن أخواته.
const NAVIGATION: ReadonlyArray<{ href: string; label: string }> = [
  //: الجذر هو المدخل الوحيد: شبكة المركبات وتبويبات حالة المزاد باسم
  //: «المزادات». لا رابط لقائمة مزادات — المزاد أسبوعي واحد، وقائمته
  //: للإدارة لا للعميل.
  { href: "/", label: "المزادات" },
  { href: "/bids", label: "مزايداتي" },
  { href: "/favourites", label: "مفضّلتي" },
  { href: "/wallet", label: "محفظتي" },
  { href: "/purchases", label: "مشترياتي" },
  { href: "/account", label: "حسابي" },
];

export function PageShell({
  title,
  /**
   * ما يُرسم **بعرض الشاشة** قبل العنوان — لافتة الصدر مثلاً.
   *
   * لأن الشبكة تحتاج لافتةً تعبر العمود كلّه، وصفحةً تضعها داخل `children`
   * تجعلها تحت العنوان: مكانٌ آخر، وترتيبٌ يختلف من صفحة لأخرى.
   */
  banner,
  children,
}: {
  title?: string;
  banner?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-outline-variant/60 bg-surface/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1380px] items-center justify-between gap-6 px-4 md:px-8 lg:px-12">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2 whitespace-nowrap">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-on-primary">
                ح
              </span>
              <span className="text-headline-sm tracking-tight">
                حراج واحد{" "}
                <span className="tnum text-label-sm text-secondary">v2</span>
              </span>
            </Link>

            {/*
              يختفي التنقّل تحت `lg` ويحلّ محلّه الشريط الأفقيّ أسفله — لا قائمة
              منسدلة: ستّة روابط تمرّ أفقياً على ٣٧٥ بكسل، وزرّ يفتح قائمة هو
              نقرةٌ زائدة على كل انتقال.
            */}
            <nav aria-label="الأقسام" className="hidden items-center gap-1 lg:flex">
              {NAVIGATION.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-label-md text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <Link
            href="/account"
            aria-label="حسابي"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-label-sm text-on-primary"
          >
            ح
          </Link>
        </div>

        <nav
          aria-label="الأقسام"
          className="flex gap-1 overflow-x-auto border-t border-outline-variant/60 px-4 py-2 lg:hidden"
        >
          {NAVIGATION.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="whitespace-nowrap rounded-md px-3 py-1.5 text-label-md text-on-surface-variant"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-[1380px] px-4 py-8 md:px-8 lg:px-12">
        {banner}
        {title ? <h1 className="mb-6 text-headline-lg">{title}</h1> : null}
        {children}
      </main>

      <SiteFooter />
    </>
  );
}

/**
 * الذيل — اسمٌ وحقوقٌ وسطرُ أمان، **ولا روابط**.
 *
 * التصميم المرجعيّ يضع أربعة: الشروط والأحكام · لوائح الفحص · الخصوصية ·
 * الدعم. ولا واحدة منها صفحةٌ قائمة في هذا التطبيق، ورابطٌ يقود إلى 404 أسوأ
 * من غيابه — يُقرأ عطلاً في المنتج لا نقصاً في المحتوى. تُضاف مع صفحاتها.
 */
function SiteFooter() {
  return (
    <footer className="mt-16 w-full border-t border-outline-variant/60 bg-surface-low">
      <div className="mx-auto flex max-w-[1380px] flex-col gap-3 px-4 py-10 text-body-sm text-on-surface-variant md:flex-row md:items-center md:justify-between md:px-8 lg:px-12">
        <p>
          © 2026 منصة حراج واحد <span className="tnum">v2</span> للمزادات. جميع
          الحقوق محفوظة — المملكة العربية السعودية.
        </p>
        <p className="flex items-center gap-2 text-caption">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-secondary" />
          المزايدة مغلقة ومشفَّرة
        </p>
      </div>
    </footer>
  );
}
