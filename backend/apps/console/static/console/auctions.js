/* شاشة المزادات: النوافذ الأربع، وتخصيص الأعمدة. T846.
 *
 * ولماذا بلا إطارٍ ولا مكتبة
 * ---------------------------------------------------------------------------
 * الطلب ذكر DataTables و SweetAlert2. وما تفعله المكتبتان هنا يفعله المتصفّح
 * وحده اليوم:
 *
 * * **الترقيم والفرز** يجريان على الخادم أصلاً — `Paginator` وقائمةُ فلاتر
 *   تعود في العنوان. وDataTables يجلب الصفوف كلَّها ليرقّمها في المتصفّح،
 *   وهو بالضبط ما لا يُحتمل مع ٥٦ مزاداً كلٌّ منها بستّ إحصاءات مجمَّعة.
 * * **النافذة** عنصرٌ في المعيار: `<dialog>` يحبس التركيز، ويُغلق بـEscape،
 *   ويعتم ما خلفه بـ`::backdrop`، ويُعلن نفسه نافذةً لقارئ الشاشة. أربعةُ
 *   أشياء كان كلٌّ منها سطراً يُنسى.
 * * **التأكيد** جملةٌ داخل النافذة فوق زرّ التنفيذ، والنتيجة تمرّ بـ
 *   `django.contrib.messages` — القناةُ التي تستعملها اللوحة كلّها. ونظاما
 *   إشعارٍ على شاشةٍ واحدة يعني رسالتين بشكلين لفعلين متشابهين.
 *
 * فالثمنُ المُوفَّر ليس بايتات المكتبة وحدها، بل نظامُ تنسيقٍ ثانٍ وسلوكُ
 * وصولٍ ثانٍ على شاشةٍ واحدة.
 */
(function () {
  "use strict";

  /* النموذج يُوجَّه عند الفتح: القالب يبني المسار بـ`{% url %}` على المزاد
     رقم **صفر** — نائبٌ لا وجود له — والسطر أدناه يستبدله برقم الصفّ. فالمسار
     مشتقٌّ من اسمه في `urls.py` ولا يُكتب بيدٍ هنا ولا هناك.
     ولا نموذج في كل صفّ — خمسةٌ وعشرون صفّاً × أربعُ نوافذ = مئةُ نموذجٍ
     مخفيّ في كل تحميل، ومئةُ حقلِ CSRF معها. */
  function openWith(dialog, source, fields) {
    if (!dialog) return;

    var form = dialog.querySelector("form");
    form.action = form.getAttribute("data-action").replace("/0/", "/" + source.dataset.pk + "/");

    var label = dialog.querySelector("[data-number]");
    if (label) label.textContent = source.dataset.number || "";

    for (var i = 0; i < fields.length; i++) {
      var name = fields[i];
      var input = dialog.querySelector("[data-" + name + "]");
      if (input && source.dataset[name] !== undefined) input.value = source.dataset[name];
    }

    dialog.showModal();
  }

  /* حقول الموعد تظهر لـ«قريباً» و«نشط» وحدهما.
     والمنطق هنا **عرضٌ فقط**: الخادم يفحص الشرط نفسه ويرفض بدونه، لأن
     إخفاءَ حقلٍ ليس تحقّقاً — من يرسل الطلب بيده لا يرى الإخفاء. */
  var TIMED = { soon: true, active: true };

  function syncTimeFields(dialog) {
    var choice = dialog.querySelector("[data-badge]");
    if (!choice) return;
    var timed = TIMED[choice.value] === true;
    var shown = dialog.querySelector("[data-when-timed]");
    var hint = dialog.querySelector("[data-when-untimed]");
    if (shown) shown.hidden = !timed;
    if (hint) hint.hidden = timed;
    var boxes = dialog.querySelectorAll("[data-when-timed] input");
    for (var i = 0; i < boxes.length; i++) boxes[i].required = timed;
  }

  document.addEventListener("click", function (event) {
    var hit = function (selector) {
      return event.target.closest ? event.target.closest(selector) : null;
    };

    var status = hit("[data-open-status]");
    if (status) {
      var statusModal = document.getElementById("statusModal");
      openWith(statusModal, status, ["starts", "ends"]);
      var choice = statusModal.querySelector("[data-badge]");
      if (choice) choice.value = status.dataset.badge;
      syncTimeFields(statusModal);
      return;
    }

    var reschedule = hit("[data-open-reschedule]");
    if (reschedule) {
      openWith(document.getElementById("rescheduleModal"), reschedule,
               ["starts", "ends", "sms"]);
      return;
    }

    var fees = hit("[data-open-fees]");
    if (fees) {
      openWith(document.getElementById("feesModal"), fees, ["deposit", "fee"]);
      return;
    }

    var ending = hit("[data-open-end]");
    if (ending) {
      openWith(document.getElementById("endModal"), ending, []);
      return;
    }

    var close = hit("[data-close]");
    if (close) {
      var box = close.closest("dialog");
      if (box) box.close();
    }
  });

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-badge]")) {
      syncTimeFields(event.target.closest("dialog"));
    }
  });

  /* ------------------------------------------------------------------------
     تخصيص الأعمدة
     ------------------------------------------------------------------------
     الإخفاء بـ`hidden` على كل `<th>` و`<td>` يحمل `data-col` نفسه — لا على
     `<col>`: عنصر `<col>` لا يقبل `display:none` في المتصفّحات، وهي حيلةٌ
     تُكتب كثيراً ولا تعمل.

     والاختيار في `localStorage` لأنه تفضيلُ **جهاز** لا تفضيلُ حساب: الموظّف
     نفسه يريد أعمدةً أقلّ على لوحه وأكثر على شاشة المكتب. وحفظُه على الخادم
     يعني حقلاً وهجرةً وطلبَ كتابةٍ عند كل نقرة خانة. */
  var KEY = "haraj.console.auctions.columns";

  function readHidden() {
    try {
      return JSON.parse(window.localStorage.getItem(KEY) || "[]") || [];
    } catch (e) {
      /* التصفّح الخاص يرمي عند القراءة نفسها في بعض المتصفّحات. شاشةٌ
         تتعطّل لأن التفضيل لم يُقرأ أسوأ من شاشةٍ بكل أعمدتها. */
      return [];
    }
  }

  function applyColumns(hidden) {
    var cells = document.querySelectorAll("[data-col]");
    for (var i = 0; i < cells.length; i++) {
      cells[i].hidden = hidden.indexOf(cells[i].getAttribute("data-col")) !== -1;
    }
    var boxes = document.querySelectorAll("[data-column]");
    for (var j = 0; j < boxes.length; j++) {
      boxes[j].checked = hidden.indexOf(boxes[j].getAttribute("data-column")) === -1;
    }
  }

  var hiddenColumns = readHidden();
  applyColumns(hiddenColumns);

  document.addEventListener("change", function (event) {
    var box = event.target.closest ? event.target.closest("[data-column]") : null;
    if (!box) return;

    var key = box.getAttribute("data-column");
    var at = hiddenColumns.indexOf(key);
    if (box.checked && at !== -1) hiddenColumns.splice(at, 1);
    if (!box.checked && at === -1) hiddenColumns.push(key);

    applyColumns(hiddenColumns);
    try {
      window.localStorage.setItem(KEY, JSON.stringify(hiddenColumns));
    } catch (e) { /* ممتلئ أو محظور — الاختيار يعمل هذه الجلسة ولا يُحفظ. */ }
  });
})();
