/* نوافذُ شاشة الأدوار — إنشاءٌ وتحكّمٌ في الصلاحيات. T856.
 *
 * **`<dialog>` لا `<div>` بطبقةٍ مرسومة باليد.** المتصفّح يحبس التركيز
 * بداخلها، ويُغلقها بـEscape، ويعتم ما خلفها بـ`::backdrop`، ويُعلنها نافذةً
 * لقارئ الشاشة — أربعةُ أشياء كان كلٌّ منها سطرَ جافاسكربت يُنسى واحدٌ منها
 * دائماً.
 *
 * **ونافذةٌ واحدة تُملأ من الصفّ، لا نافذةٌ في كل صفّ.** سبعةُ أدوارٍ ×
 * نافذتين = أربعَ عشرةَ استمارةً مخفيّة في كل تحميل، ومعها أربعةَ عشرَ حقلَ
 * CSRF. فالصفُّ يحمل بياناته في `data-*`، والنافذةُ تُملأ منها عند الفتح.
 *
 * **والمسار مشتقٌّ من اسمه لا مكتوبٌ بيد:** القالب يطبع `{% url … 'x' %}`
 * بنائبٍ نصّيّ، وهذا يستبدله بمعرّف الصفّ — فبادئةُ اللوحة تبقى في مكانٍ
 * واحد (`ops/checks/console_urls_are_named.py`).
 */
(function () {
  "use strict";

  var PLACEHOLDER = "__slug__";

  function dialogOf(id) {
    return document.getElementById(id);
  }

  /* املأ نافذة الصلاحيات من الصفّ: الاسمُ في العنوان، والمربّعاتُ المؤشَّرة
     هي ما يحمله الدور الآن. */
  function fillCapabilities(dialog, source) {
    var form = dialog.querySelector("form");
    form.action = form
      .getAttribute("data-action")
      .replace(PLACEHOLDER, source.dataset.slug);

    var title = dialog.querySelector("[data-role-label]");
    if (title) title.textContent = source.dataset.label || "";

    var held = dialog.querySelector("[data-role-held]");
    if (held) held.textContent = source.dataset.held || "0";

    /* `data-caps` قائمةٌ مفصولةٌ بفاصلة. والمقارنةُ على مجموعةٍ لا على نصّ:
       `indexOf` على السلسلة يُطابق `users.view` داخل `users.viewer` لو وُجد
       يوماً — وهي مطابقةٌ تمرّ في الاختبار وتُخطئ في الإنتاج. */
    var carried = {};
    (source.dataset.caps || "").split(",").forEach(function (name) {
      if (name) carried[name] = true;
    });

    var boxes = dialog.querySelectorAll('input[name="capabilities"]');
    for (var i = 0; i < boxes.length; i++) {
      boxes[i].checked = carried[boxes[i].value] === true;
    }

    /* السببُ يُفرَّغ عند كل فتح: سببٌ باقٍ من تعديلٍ سابق يُرسَل مع تعديلٍ
       آخر، فيقرأ المدقّق سبباً لا يخصّ ما وقع. */
    var reason = dialog.querySelector('[name="reason"]');
    if (reason) reason.value = "";

    dialog.showModal();
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-opens]");
    if (!opener) return;

    var dialog = dialogOf(opener.dataset.opens);
    if (!dialog) return;

    event.preventDefault();
    if (opener.dataset.slug) {
      fillCapabilities(dialog, opener);
    } else {
      dialog.showModal();
    }
  });

  /* الإغلاق بزرّ مُعلَن لا بضغطةٍ على الخلفية وحدها: من يفتح نافذةً بلوحة
     المفاتيح يحتاج زرّاً يصله بـTab. وEscape يعمل من المتصفّح بلا سطرٍ هنا. */
  document.addEventListener("click", function (event) {
    var closer = event.target.closest("[data-close]");
    if (!closer) return;
    var dialog = closer.closest("dialog");
    if (dialog) dialog.close();
  });
})();
