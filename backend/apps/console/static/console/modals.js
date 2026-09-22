/* أيُّ رابطٍ في اللوحة يُفتح نافذةً. T970
   ======================================

   طلبُ المالك (٢٢ سبتمبر ٢٠٢٦): «المركبة لما أضغط عليها، هي والفاتورة
   والمشتري وكل الداتا اللي ممكن تتعرض، المفروض تكون كلها بوبات».

   ## وسمةٌ واحدةٌ على الرابط، لا سكربتٌ لكلّ شاشة

   `<a data-modal href="…">` وكفى. والوجهةُ تُجلَب بـ`?modal=1` فيردُّ الخادمُ
   **الشاشةَ نفسَها في إطارٍ عارٍ** (`console/modal_base.html`) — لا قالبَ
   ثانياً يتفارق مع أصله.

   ## ولماذا ليست كلَّ الروابط تلقائيّاً

   الشريطُ الجانبيُّ روابط، والصفحاتُ روابط، والمرشّحاتُ روابط. وتحويلُ كلّ
   `<a>` إلى نافذةٍ يجعل «التالي» يفتح صفحةَ الجدول داخل نافذةٍ فوق الجدول.
   فالوسمُ صريح: من أراد نافذةً كتبها.

   ## وثلاثةُ أشياءَ يفعلها ولها سبب

   * **`Ctrl`/`⌘`/الزرُّ الأوسط يمرّون** إلى التبويب الجديد كما يتوقّع كلُّ
     من يفتح شيئاً في تبويبٍ ثانٍ. ونافذةٌ تبتلع `Ctrl+click` تكسر عادةً
     راسخةً بلا مقابل.
   * **والرابطُ يبقى `href` حقيقيّاً**: يُنسَخ، ويُفتح في تبويب، ويعمل قبل أن
     يصل أيُّ سكربت. وزرٌّ بـ`data-url` كان سيفقد الثلاثة.
   * **و`Esc` والنقرُ على الخلفيّة يُغلقان** — سلوكُ `<dialog>` نفسِه، بلا
     شيفرة.

   ## وتداخلُ النوافذ ممنوع

   نافذةٌ داخل نافذةٍ تُغلق الأولى فيضيع مكانُ القارئ. فالرابطُ داخل نافذةٍ
   **يُحمَّل في مكانها** لا في ثانية: `data-modal` داخل الجسم المحقون يعيد
   استعمال الغلاف نفسِه. */
(function () {
  "use strict";

  var host = document.querySelector("[data-page-modal]");
  var body = host ? host.querySelector("[data-page-modal-body]") : null;
  if (!host || !body || !host.showModal) return;

  /** أضِف `?modal=1` إلى الرابط بلا أن تُتلف مرشّحاتِه. */
  function asModal(href) {
    return href + (href.indexOf("?") === -1 ? "?" : "&") + "modal=1";
  }

  function open(href) {
    body.innerHTML = '<p class="empty">يُحمَّل…</p>';
    if (!host.open) host.showModal();
    fetch(asModal(href), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "fetch" },
    })
      .then(function (response) {
        if (!response.ok) throw new Error(response.status);
        return response.text();
      })
      .then(function (html) {
        body.innerHTML = html;
        dress(body, href);
        var full = body.querySelector("[data-modal-full]");
        if (full) full.setAttribute("href", href);
        var closer = body.querySelector("[data-modal-close]");
        if (closer) {
          closer.addEventListener("click", function () { host.close(); });
        }
        wire(body);
      })
      .catch(function () {
        // الفشلُ يُقال ولا يُترك فراغاً: نافذةٌ فارغةٌ تُقرأ «لا بيانات»،
        // وهي جملةٌ كاذبة.
        body.innerHTML =
          '<p class="empty">تعذّر تحميلُ هذه البيانات — أعِد المحاولة.</p>';
      });
  }

  /* **قِطعةٌ لا ترث الإطار: يُلبسها الغلافُ رأساً.** T970

     `console:vehicle-bid-list` وأخواتُها **قِطَعٌ بحكم التصميم** — كُتبت
     لتُحقَن في نوافذَ خمسِ شاشاتٍ لكلٍّ منها رأسُها، فلا تمتدّ إطاراً ولا
     تحمل زرَّ إغلاق. ولو أُجبرت على امتداد `_modal_base` لظهر لتلك الخمسِ
     رأسان.

     فالغلافُ يسأل: أجاء المحتوى برأسٍ؟ فإن لم يأتِ ألبسه واحداً. والقِطعةُ
     تبقى كما هي، والخمسُ لا تتغيّر. */
  var CLOSE = "M6 6l12 12M18 6 6 18";

  function dress(root, href) {
    if (root.querySelector("[data-modal-close]")) return;
    var head = document.createElement("div");
    head.className = "images-modal__head";
    var title = root.querySelector("h1, h2, h3");
    head.innerHTML =
      '<h3 class="images-modal__title">' +
      (title ? title.textContent.trim() : "تفاصيل") +
      '</h3><button type="button" class="modal__close" data-modal-close ' +
      'aria-label="إغلاق"><svg viewBox="0 0 24 24" width="16" height="16" ' +
      'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true"><path d="' + CLOSE + '"/></svg></button>';
    if (title) title.remove();
    var foot = document.createElement("div");
    foot.className = "page-modal__foot";
    foot.innerHTML = '<a data-modal-full>افتحها صفحةً كاملة ←</a>';
    var shell = document.createElement("div");
    shell.className = "page-modal__body";
    while (root.firstChild) shell.appendChild(root.firstChild);
    root.appendChild(head);
    root.appendChild(shell);
    root.appendChild(foot);
  }

  function wire(root) {
    root.querySelectorAll("a[data-modal]").forEach(function (link) {
      if (link.dataset.modalWired) return;
      link.dataset.modalWired = "1";
      link.addEventListener("click", function (event) {
        // تبويبٌ جديدٌ يمرّ — انظر رأس الملفّ.
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
          return;
        }
        event.preventDefault();
        open(link.getAttribute("href"));
      });
    });
  }

  wire(document);
})();
