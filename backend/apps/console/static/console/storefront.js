/* نوافذُ شاشتَي «شريط الأخبار» و«الباقات». T921.
 *
 * **`<dialog>` لا `<div>` بطبقةٍ مرسومة** — للسبب المكتوب في `roles.js`:
 * المتصفّح يحبس التركيز، ويُغلق بـEscape، ويعتم الخلف، ويُعلنها نافذةً
 * لقارئ الشاشة.
 *
 * **ولا مِلءَ من `data-*` هنا، بخلاف `roles.js`.** هناك نافذةٌ واحدةٌ تُملأ
 * من الصفّ لأن البديل مئةٌ وستّةٌ وعشرون مربّعاً مخفيّاً؛ وهنا الاستمارةُ
 * أربعةُ حقول، والصفوفُ في v1 ثلاثةٌ وواحد. فالخادمُ يرسم استمارةً لكلّ
 * صفّ — والثمنُ الذي يشتريه ذلك أن **الرفضَ يعود بأخطائه بجانب حقولها
 * وبما كتبه الموظّف**، لا نافذةً تُفتح فارغةً ورسالةً فوق الجدول.
 *
 * فما بقي لهذا الملفّ سطران: افتح، وأغلق.
 */
(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-opens]");
    if (!opener) return;
    var dialog = document.getElementById(opener.dataset.opens);
    if (!dialog) return;
    event.preventDefault();
    dialog.showModal();
  });

  document.addEventListener("click", function (event) {
    var closer = event.target.closest("[data-close]");
    if (!closer) return;
    var dialog = closer.closest("dialog");
    if (dialog) dialog.close();
  });

  /* الاستمارةُ المرفوضة تُعاد مفتوحة: الخادمُ يكتب اسمَ نافذتها في
     `data-open-dialog`، وبلا هذا يقرأ الموظّفُ صفحةً تبدو كأن شيئاً لم
     يقع — وقد كتب فيها. */
  var page = document.querySelector("[data-open-dialog]");
  if (page) {
    var reopen = document.getElementById(page.dataset.openDialog);
    if (reopen) reopen.showModal();
  }
})();
