/**
 * رسمةُ الصفحة — خطٌّ خفيفٌ في زاويتها يقول شغلها. الأسلوب «أ».
 *
 * اقتراحُ المالك (٧ أكتوبر ٢٠٢٦): «على حسب كل صفحة والتاسك اللي بتعمله نضيف
 * رسمة ورا في الخلفية تعبّر عن الصفحة … مش حنغيّر حاجة في المحتوى».
 *
 * **ولذلك هي خارج المحتوى بالبناء:** `position: fixed` في الزاوية المقابلة
 * لبداية القراءة (يسار الشاشة في RTL) فلا تقع تحت عنوانٍ يُقرأ أوّلاً، و
 * `pointer-events: none` فلا تأخذ نقرة، و`aria-hidden` فلا يقرؤها قارئُ الشاشة.
 * والشفافيّةُ على الرسمة لا على نصّ (`palette.md` §٣-٣)، ولونُها كحليُّ الباليت.
 *
 * رسومٌ خطّيّةٌ مضمَّنة لا صور: لا ملفَّ يُحمَّل، وتتلوّن من `currentColor`.
 */

const ART = {
  //: صفحةُ المركبة — هيكلُ سيّارةٍ وعجلتاه.
  car: (
    <>
      <path d="M40 150h22a18 18 0 0 1 36 0h104a18 18 0 0 1 36 0h22v-30l-26-8-38-36H110L74 112l-34 8z" />
      <circle cx="80" cy="150" r="14" />
      <circle cx="220" cy="150" r="14" />
      <path d="M116 80l-28 30h70V80z" />
      <path d="M170 80v30h52l-30-30z" />
      <path d="M30 186h240" />
    </>
  ),
  //: المزاد — مظروفٌ مختوم (المزايدةُ المغلقة) ومطرقةُ الترسية.
  auction: (
    <>
      <rect x="40" y="70" width="150" height="100" rx="8" />
      <path d="M40 76l75 52 75-52" />
      <circle cx="115" cy="140" r="12" />
      <path d="M200 176l52-52" />
      <rect x="228" y="70" width="58" height="30" rx="6" transform="rotate(45 257 85)" />
      <path d="M190 196h80" />
    </>
  ),
} as const;

export type PageArtName = keyof typeof ART;

export function PageArt({ name }: { name: PageArtName }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 300 220"
      className="page-art"
      fill="none"
      stroke="currentColor"
      strokeWidth="5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ART[name]}
    </svg>
  );
}
