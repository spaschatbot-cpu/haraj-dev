/* منصّةُ الملّاك — نافذةُ صور المركبة، وحارسُ الحكم. T965
   =====================================================

   ## لماذا ملفٌّ ثابتٌ لا `<script>` في القالب

   شاشةُ المزاد تحمل نظيرَ هذا السلوك مكتوباً **داخل** `auction_detail.html`،
   وهو ما جعله غيرَ قابلٍ للاستعمال هنا: نسخُه كان سيعني منطقاً واحداً في
   موضعين يُصلَح في أحدهما ويُنسى في الآخر — العطلُ المكرَّرُ في هذا المستودع
   (T922 · T929). فهو ملفٌّ يحمل بصمتَه (`?v=`) ويُخزَّن في كاش المتصفّح، ولا
   يُعاد إرسالُه مع كلّ صفحة.

   ## والصورُ تُجلَب عند الضغط

   ثلاثمئةُ صفٍّ × ستُّ صورٍ = صفحةٌ لا تُحمَّل. فالخليّةُ تحمل **العدد**
   وحدَه، والضغطُ يجلب `vehicle-images?modal=1` — وهو القالبُ نفسُه الذي
   تفتحه شاشةُ المزاد، فمعرضٌ واحدٌ لا اثنان.

   ## وحارسُ الحكم

   «قبول» و«رفض» فعلان لا رجعةَ لهما يُضغَط عليهما أربعين مرّةً بعد كلّ مزاد،
   والخطأُ فيهما ترسيةٌ على المركبة الخطأ. فيُسأل قبلهما سؤالٌ **يسمّي اللوت
   والمبلغ** — لا «هل أنت متأكّد؟» التي تُقرأ بعد الثالثة بلا قراءة.

   وهو حارسٌ في المتصفّح، **وليس هو الحارس**: البوّابةُ في `partners.py`
   و`POST` وحدَه، وهذا يمنع الزلّة لا الخصم. */
(function () {
  "use strict";

  // ── نافذةُ الصور ─────────────────────────────────────────────────────────
  var dialog = document.querySelector("[data-gallery-dialog]");
  var body = dialog ? dialog.querySelector("[data-gallery-body]") : null;

  if (dialog && body && dialog.showModal) {
    document.querySelectorAll("[data-gallery]").forEach(function (button) {
      button.addEventListener("click", function () {
        // نصٌّ قبل الجلب: بلا شيءٍ تُفتح نافذةٌ فارغةٌ فتُقرأ «لا صور».
        body.innerHTML = '<p class="empty">يُحمَّل المعرض…</p>';
        dialog.showModal();
        fetch(button.getAttribute("data-url"), {
          credentials: "same-origin",
          headers: { "X-Requested-With": "fetch" },
        })
          .then(function (response) {
            if (!response.ok) throw new Error(response.status);
            return response.text();
          })
          .then(function (html) {
            body.innerHTML = html;
            var closer = body.querySelector("[data-images-close]");
            if (closer) {
              closer.addEventListener("click", function () { dialog.close(); });
            }
          })
          .catch(function () {
            // الفشلُ يُقال ولا يُترك فراغاً: نافذةٌ فارغةٌ تُقرأ «لا صور
            // لهذه المركبة»، وهي جملةٌ كاذبة.
            body.innerHTML =
              '<p class="empty">تعذّر تحميلُ الصور — أعِد المحاولة.</p>';
          });
      });
    });
  }

  /* ── نافذةُ المزايدين ─────────────────────────────────────────────────────
     طلبُ المالك: «قائمة المزايدين عايزها بوباب يعرض قائمة المزايدين بس».
     وتُجلَب من `partners.offers` نفسِها بـ`?modal=1` — لا استعلامَ ثانٍ ولا
     قالبَ يتفارق مع صفحته.

     و«رسِّ على هذا» داخلها **يُرسَل كنموذجٍ عاديّ** لا بـAJAX: الترسيةُ فعلٌ
     يغيّر الفاتورةَ والحجزَ ويكتب السجلَّ، ونتيجتُه رسالةٌ تُقرأ على الصفحة.
     وصفحةٌ تُعاد بعده أصدقُ من نافذةٍ تُغلَق صامتةً. */
  var bidders = document.querySelector("[data-bidders-dialog]");
  var bidBody = bidders ? bidders.querySelector("[data-bidders-body]") : null;

  if (bidders && bidBody && bidders.showModal) {
    document.querySelectorAll("[data-bidders]").forEach(function (button) {
      button.addEventListener("click", function () {
        bidBody.innerHTML = '<p class="empty">تُحمَّل قائمةُ المزايدين…</p>';
        bidders.showModal();
        fetch(button.getAttribute("data-url"), {
          credentials: "same-origin",
          headers: { "X-Requested-With": "fetch" },
        })
          .then(function (response) {
            if (!response.ok) throw new Error(response.status);
            return response.text();
          })
          .then(function (html) {
            bidBody.innerHTML = html;
            var closer = bidBody.querySelector("[data-modal-close]");
            if (closer) {
              closer.addEventListener("click", function () { bidders.close(); });
            }
          })
          .catch(function () {
            bidBody.innerHTML =
              '<p class="empty">تعذّر تحميلُ قائمة المزايدين — أعِد المحاولة.</p>';
          });
      });
    });
  }

  // ── حارسُ الحكم ──────────────────────────────────────────────────────────
  // **تفويضٌ على المستند** لا ربطٌ لكلّ استمارةٍ عند الإقلاع: استماراتُ
  // «قبول» داخل نافذة المزايدين تُحقَن بعد أن يكون هذا السكربتُ قد عمل،
  // فالربطُ المباشرُ لا يبلغها أبداً — وهي أخطرُها: ترسيةٌ لا رجعةَ لها.
  //
  // **والسؤالُ نافذةُ اللوحة لا `window.confirm`** (٢٤ سبتمبر ٢٠٢٦). كان
  // `confirm` أصليّاً: يرسمه نظامُ التشغيل بأسلوبه وخطّه وعنوانه («haraj.spas.sa
  // يقول»)، ويجمّد الصفحةَ كلَّها وهو مفتوح — بينما كلُّ سؤالٍ آخرَ في اللوحة
  // نافذةٌ منها («إنهاء فوري» و«تغيير الحالة» في شاشة المزادات). وقاعدةُ T837
  // في `app.css` هي نفسُها: ما يرسمه النظامُ يختلف بين جهازٍ وجهاز. وظهر ذلك
  // في اختبار المسار الكامل على الخادم: الضغطُ على «قبول» جمّد الصفحة ولم
  // يستطع مُشغِّلُ المتصفّح الآليّ أن يجيب النافذة الأصليّة.
  var ask = null;

  function decide(text, yes) {
    if (typeof HTMLDialogElement === "undefined") {
      // متصفّحٌ بلا `<dialog>` — السؤالُ الأصليّ خيرٌ من ترسيةٍ بلا سؤال.
      if (window.confirm(text)) yes();
      return;
    }
    if (!ask) {
      ask = document.createElement("dialog");
      ask.className = "modal";
      ask.innerHTML =
        '<form method="dialog">' +
        "<h2>تأكيد القرار</h2>" +
        "<p data-decide-text></p>" +
        '<p class="modal__buttons">' +
        '<button type="submit" value="yes">تأكيد</button>' +
        // «تراجع» زرٌّ عاديّ لا إرسال — هيئةُ «إلغاء» في بقيّة نوافذ اللوحة
        // (`type="button" data-close`). كان `submit` فأخذ لونَ «تأكيد» نفسَه،
        // وزرّان متطابقان تحت سؤالٍ لا رجعةَ فيه يُضغط أحدُهما بلا قراءة.
        '<button type="button" data-close>تراجع</button>' +
        "</p></form>";
      ask.querySelector("[data-close]").addEventListener("click", function () {
        ask.close("no");
      });
      document.body.appendChild(ask);
    }
    // `textContent` لا `innerHTML`: السؤالُ يحمل اسمَ المزايد كما كتبه هو.
    ask.querySelector("[data-decide-text]").textContent = text;
    ask.returnValue = "";
    ask.onclose = function () {
      if (ask.returnValue === "yes") yes();
    };
    ask.showModal();
  }

  document.addEventListener("submit", function (event) {
    var form = event.target.closest ? event.target.closest("[data-decide]") : null;
    if (!form) return;
    // أُجيب السؤالُ للتوّ: الإرسالُ الثاني هو الإرسال.
    if (form.getAttribute("data-decided") === "1") {
      form.removeAttribute("data-decided");
      return;
    }
    event.preventDefault();
    var submitter = event.submitter || null;
    decide(form.getAttribute("data-decide"), function () {
      form.setAttribute("data-decided", "1");
      if (form.requestSubmit) form.requestSubmit(submitter);
      else form.submit();
    });
  });
})();
