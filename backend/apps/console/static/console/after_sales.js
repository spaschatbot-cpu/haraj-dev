/* نافذةُ الفاتورة في «ما بعد البيع». T869.
 *
 * **البيانات من الصفّ لا من الخادم.** v1 يطلب النافذة بـ`fetch` لكل ضغطة على
 * «عرض»، فلكل نظرةٍ على فاتورةٍ رحلةُ شبكةٍ وانتظارٌ واحتمالُ خطأٍ **داخل**
 * نافذة. والأرقامُ الستّة معروضةٌ أصلاً في الصفحة التي رُسمت، فتُقرأ من
 * `data-*`.
 *
 * **و`<dialog>` لا `<div>` بطبقةٍ مرسومة:** المتصفّح يحبس التركيز، ويُغلق
 * بـEscape، ويُعتم الخلف بـ`::backdrop`، ويُعلنها نافذةً لقارئ الشاشة —
 * أربعةٌ كان كلٌّ منها سطرَ جافاسكربت يُنسى واحدٌ منها دائماً.
 *
 * **ونافذةٌ واحدة تُملأ، لا نافذةٌ في كل صفّ:** خمسون صفّاً × سبعةَ عشرَ
 * عنصراً = ثمانمئةٍ وخمسون عنصراً مخفيّاً في كل تحميل.
 */
(function () {
  "use strict";

  /* اسمُ الخاصّة في الصفّ ← مكانُها في النافذة. مكتوبةٌ مرّةً: قائمتان
     تُنسى إحداهما عند إضافة حقل، فيظهر الحقلُ فارغاً بلا رسالة. */
  var FIELDS = [
    "vehicle", "number", "state", "odoo", "amount", "paid", "residual", "sheet",
  ];

  function fill(dialog, source) {
    for (var i = 0; i < FIELDS.length; i++) {
      var slot = dialog.querySelector("[data-inv-" + FIELDS[i] + "]");
      if (slot) slot.textContent = source.dataset[FIELDS[i]] || "—";
    }

    /* الرابطُ إلى صفحة الفاتورة يُبنى في القالب بـ`{% url %}`، فبادئةُ اللوحة
       تبقى في `urls.py` وحدها ولا تُكتب هنا بيد. */
    var link = dialog.querySelector("[data-inv-href]");
    if (link) link.setAttribute("href", source.dataset.href || "#");

    dialog.showModal();
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-opens]");
    if (opener) {
      var dialog = document.getElementById(opener.dataset.opens);
      if (dialog) {
        event.preventDefault();
        fill(dialog, opener);
      }
      return;
    }

    /* الإغلاق بزرٍّ مُعلَن لا بضغطةٍ على الخلفية وحدها: من يفتح النافذة بلوحة
       المفاتيح يحتاج زرّاً يصله بـTab. وEscape يعمل من المتصفّح بلا سطرٍ هنا. */
    var closer = event.target.closest("[data-close]");
    if (closer) {
      var open = closer.closest("dialog");
      if (open) open.close();
    }
  });
})();
