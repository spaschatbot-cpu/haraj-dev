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

  /* أنماطُ ورقةِ الطباعة — مضمَّنةٌ في الـ`iframe` لأنه مستندٌ مستقلّ لا يرث
     أنماطَ الصفحة. مبنيّةٌ على `.voucher__*` نفسِها بألوانٍ للورق. */
  var PRINT_STYLE =
    "body{font-family:system-ui,'Segoe UI',sans-serif;direction:rtl;color:#111;margin:24px;font-size:14px}" +
    "h2{margin:0 0 .2rem;font-size:1.3rem}h3{margin:0 0 .4rem;font-size:.8rem;color:#666;font-weight:700}" +
    ".voucher__num{margin:.1rem 0 0;color:#666;font-size:.9rem}" +
    ".voucher__head{border-bottom:2px solid #333;padding-bottom:.6rem;margin-bottom:1rem}" +
    ".voucher__grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}" +
    ".record{margin:0}.record__pair{display:flex;justify-content:space-between;gap:1rem;" +
    "padding:.35rem 0;border-bottom:1px dashed #ddd}.record__pair dt{color:#666}" +
    ".record__pair dd{margin:0;font-weight:700;text-align:end}" +
    ".voucher__total{font-size:1.1rem}.pill{font-weight:700}" +
    ".empty{color:#888;font-size:.8rem;margin-top:1rem}";

  /* الطباعة عبر `<iframe>` مستقلّ — لا طباعةَ الصفحة نفسها.
     `<dialog open>` في «الطبقة العليا» يُرسَم فوق أيّ طباعةٍ للصفحة مهما
     أخفينا خلفَه، فتخرج صفحةٌ فارغة (وقع مراراً). فالحلُّ مستندٌ آخرُ تماماً:
     `iframe` مخفيٌّ يُكتب فيه جسمُ السند بأنماطه، ويُطبَع هو وحدَه. ولا نافذةَ
     منبثقةً تحجبها موانعُ النوافذ — الإطارُ داخل الصفحة. */
  function printVoucher(dialog) {
    var doc = dialog.querySelector(".voucher__doc");
    if (!doc) {
      window.print();
      return;
    }

    var frame = document.getElementById("voucherPrintFrame");
    if (!frame) {
      frame = document.createElement("iframe");
      frame.id = "voucherPrintFrame";
      frame.setAttribute("aria-hidden", "true");
      frame.style.cssText =
        "position:fixed;inset-inline-end:0;inset-block-end:0;inline-size:0;block-size:0;border:0;";
      document.body.appendChild(frame);
    }

    var fdoc = frame.contentWindow.document;
    fdoc.open();
    fdoc.write(
      '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">' +
        "<title>سند دفع</title><style>" +
        PRINT_STYLE +
        "</style></head><body>" +
        doc.innerHTML +
        "</body></html>",
    );
    fdoc.close();

    /* الطباعةُ بعد أن يكتمل رسمُ الإطار: نافذته تُطلق `load`، ونطبع حينها.
       وبعضُ المتصفّحات يكمل فوراً، فمهلةٌ قصيرةٌ احتياط. */
    var doPrint = function () {
      frame.contentWindow.focus();
      frame.contentWindow.print();
    };
    if (frame.contentWindow.document.readyState === "complete") {
      setTimeout(doPrint, 50);
    } else {
      frame.contentWindow.onload = doPrint;
    }
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
