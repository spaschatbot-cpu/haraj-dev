/* سندُ الدفع في «ما بعد البيع». T869.
 *
 * **البيانات من الصفّ لا من الخادم.** v1 يفتح `<iframe>` يحمّل صفحةً كاملة من
 * `/invoice?inv=…` (مستند HTML + Bootstrap) لكل ضغطة على «عرض». والحقولُ كلُّها
 * مرسومةٌ أصلاً في الصفّ، فتُقرأ من `data-*` بلا رحلةِ شبكةٍ ولا انتظار.
 *
 * **و`<dialog>` لا `<div>` بطبقةٍ مرسومة:** المتصفّح يحبس التركيز، ويُغلق
 * بـEscape، ويُعتم الخلف بـ`::backdrop`، ويُعلنها نافذةً لقارئ الشاشة.
 *
 * **والطباعةُ بنسخةٍ لا بالنافذة:** `<dialog open>` في «الطبقة العليا»، وطباعتُها
 * bug في المتصفّح يُخرج صفحةً فارغة. فيُنسَخ جسمُ السند إلى عنصرٍ في التدفّق
 * العاديّ (`#voucherPrint`) ويُطبَع هو، ثم يُفرَّغ.
 */
(function () {
  "use strict";

  /* اسمُ الخاصّة في الصفّ ← `[data-inv-<اسم>]` في النافذة. مكتوبةٌ مرّةً:
     قائمتان تُنسى إحداهما عند إضافة حقل، فيظهر الحقلُ فارغاً بلا رسالة. */
  var FIELDS = [
    "number", "buyer", "phone", "vehicle", "lot", "auction", "plate",
    "chassis", "mileage", "amount", "paid", "residual", "state", "source",
    "odoo", "sheet", "date",
  ];

  /* نبرةُ حبّة الحالة: نفسُ منطق القالب في العمود، فلا يختلف لونُ الحالة بين
     الجدول والسند. */
  var TONE = { "مسدَّدة": "ok", "ملغاة": "bad", "مسدَّدة جزئياً": "warn" };

  function fill(dialog, source) {
    for (var i = 0; i < FIELDS.length; i++) {
      var slot = dialog.querySelector("[data-inv-" + FIELDS[i] + "]");
      if (slot) slot.textContent = source.dataset[FIELDS[i]] || "—";
    }

    var pill = dialog.querySelector("[data-inv-state-pill]");
    if (pill) pill.setAttribute("data-tone", TONE[source.dataset.state] || "plain");

    /* الرابطُ إلى صفحة الفاتورة يُبنى في القالب بـ`{% url %}`، فبادئةُ اللوحة
       تبقى في `urls.py` وحدها ولا تُكتب هنا بيد. */
    var link = dialog.querySelector("[data-inv-href]");
    if (link) link.setAttribute("href", source.dataset.href || "#");

    /* الفاتورةُ الضريبيّة تظهر فقط حين لها رابطٌ في أودو — وإلا بقيت مخفيّة:
       فاتورةٌ محليّةٌ لا فاتورةَ ضريبيّةَ لها، وزرٌّ يفتح لا شيء أسوأ من غيابه. */
    var odoo = dialog.querySelector("[data-inv-odoo-url]");
    if (odoo) {
      var odooUrl = source.dataset.odooUrl || "";
      if (odooUrl) {
        odoo.setAttribute("href", odooUrl);
        odoo.hidden = false;
      } else {
        odoo.removeAttribute("href");
        odoo.hidden = true;
      }
    }

    dialog.showModal();
  }

  /* الطباعة: انسخ جسمَ السند إلى `#voucherPrint`، اطبع، ثم فرِّغه — فلا يبقى
     ظاهراً على الشاشة ولا في طباعةٍ لاحقةٍ للصفحة. */
  function printVoucher(dialog) {
    var doc = dialog.querySelector(".voucher__doc");
    var target = document.getElementById("voucherPrint");
    if (!doc || !target) {
      window.print();
      return;
    }
    target.innerHTML = doc.innerHTML;
    var clear = function () {
      target.innerHTML = "";
      window.removeEventListener("afterprint", clear);
    };
    window.addEventListener("afterprint", clear);
    window.print();
    /* احتياطٌ لمتصفّحٍ لا يُطلق `afterprint`: تفريغٌ مؤجَّل. */
    setTimeout(clear, 1000);
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

    var printer = event.target.closest("[data-inv-print]");
    if (printer) {
      event.preventDefault();
      var host = printer.closest("dialog");
      if (host) printVoucher(host);
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
