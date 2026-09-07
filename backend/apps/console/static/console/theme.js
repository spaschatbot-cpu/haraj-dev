/* لوحة المظهر — الطيّ والمظهر واللون الأساسي. T833.
 *
 * لماذا ملفٌّ يُحمَّل **حاجزاً** في <head> بلا defer:
 * ---------------------------------------------------------------------------
 * لأن السمات (data-scheme و data-nav …) يجب أن تكون على <html> **قبل أول
 * رسم**. لو انتظرنا defer أو DOMContentLoaded لرسم المتصفّح الصفحة فاتحةً
 * والشريط مفتوحاً، ثم قلبها بعد جزءٍ من الثانية — ومضةٌ بيضاء في وجه من اختار
 * الداكن، وشريطٌ ينطوي أمام العين عند كل انتقال. الملف بضع مئات من البايتات
 * ولا يلمس الـDOM في هذه المرحلة، فثمن الحجب لا يُقاس.
 *
 * ولماذا ملفٌّ لا سطرٌ داخل <head>: سطرٌ داخل الصفحة يعني script-src
 * unsafe-inline في أي سياسة محتوىً تُكتب لاحقاً — أي فتحُ البابِ كلّه لأجل
 * أربعة أسطر.
 *
 * ولماذا المتصفّح لا الخادم: هذا تفضيلُ جهازٍ لا تفضيلُ حساب. الموظّف نفسه
 * يريد الداكن على شاشته ليلاً والفاتح على شاشة الاستقبال، وحفظُه على الخادم
 * يعني حقلاً وهجرةً وطلبَ كتابةٍ عند كل نقرةٍ على عيّنة لون.
 */
(function () {
  "use strict";

  var KEY = "haraj.console.look";

  /* القيم المسموحة مكتوبةٌ هنا لا مستنتَجة: ما يُقرأ من localStorage مدخلٌ
     يملكه من يفتح أدوات المتصفّح، وسمةٌ لا تطابق أي كتلةٍ في app.css تترك
     اللوحة بلا لونٍ أساسي أصلاً. فما ليس في القائمة يسقط إلى الافتراضي. */
  var ALLOWED = {
    scheme: ["auto", "light", "dark"],
    accent: ["azure", "violet", "teal", "emerald", "amber", "rose"],
    sidebar: ["auto", "light", "dark", "gradient"],
    nav: ["full", "mini", "off"],
    motion: ["on", "off"]
  };

  var DEFAULTS = {
    /* auto لا light: نظامُ التشغيل يعرف الوقت والإضاءة، ونحن لا. */
    scheme: "auto",
    /* الأزرق هويّةُ اللوحة التي أقرّها المالك في T819 — الخمسة الباقية خيار. */
    accent: "azure",
    /* auto لا light: الافتراضي شريطٌ يتبع المظهر. كان `light` فكان من اختار
       المظهر الداكن يرى صفحةً كحليّة وشريطاً أبيض ناصعاً بجوارها — وهو ما
       ظهر في أول معاينة. و`auto` لا يكتب أي كتلةٍ فتبقى قيم المظهر نفسه. */
    sidebar: "auto",
    nav: "full",
    motion: "on"
  };

  var root = document.documentElement;
  var dark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  /* نقطة الانكسار نفسها التي في app.css. مكتوبةٌ في مكانين لأن CSS لا تُقرأ
     من JS بلا كلفة — و`test_console_look.py` يطابقهما، فافتراقُهما يُسقط
     الحزمة لا يمرّ صامتاً. */
  var narrow = window.matchMedia ? window.matchMedia("(max-width: 56rem)") : null;
  var look;

  function read() {
    var saved = {};
    try {
      saved = JSON.parse(window.localStorage.getItem(KEY) || "{}") || {};
    } catch (e) {
      /* وضعُ التصفّح الخاص يرمي عند القراءة نفسها في بعض المتصفّحات. لوحةٌ
         تتعطّل لأن التفضيل لم يُقرأ أسوأ من لوحةٍ بالمظهر الافتراضي. */
      saved = {};
    }
    var chosen = {};
    for (var name in DEFAULTS) {
      var value = saved[name];
      chosen[name] = ALLOWED[name].indexOf(value) === -1 ? DEFAULTS[name] : value;
    }

    /* الشريط على الشاشة الضيّقة **درج**، وافتراضُ الدرج مغلق.
       بلا هذا يفتح على أول زيارةٍ من هاتف فيغطّي الصفحة كلها — ولا يعرف
       الزائرُ الجديد أن `☰` هو ما يزيحه. والحفظُ يبقى محترَماً: من طلب
       `full` صراحةً في هذه الشاشة يجده مفتوحاً. */
    if (saved.nav === undefined && narrow && narrow.matches) chosen.nav = "off";
    return chosen;
  }

  function write() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(look));
    } catch (e) { /* ممتلئ أو محظور — الاختيار يعمل هذه الجلسة ولا يُحفظ. */ }
  }

  function apply() {
    /* auto تُحَلّ هنا إلى light/dark: الورقة تعرف قيمتين لا ثلاثاً، فحسابُ
       الثالثة مرّةً واحدة هنا أرخص من تكرار استعلام الوسائط في كل كتلةٍ
       داكنة في الورقة. */
    var scheme = look.scheme;
    if (scheme === "auto") scheme = dark && dark.matches ? "dark" : "light";

    root.setAttribute("data-scheme", scheme);
    root.setAttribute("data-accent", look.accent);
    root.setAttribute("data-sidebar", look.sidebar);
    root.setAttribute("data-nav", look.nav);
    root.setAttribute("data-motion", look.motion);
  }

  look = read();
  apply();

  /* تغيّر تفضيل النظام واللوحة مفتوحة: من اختار auto يعني «اتبع النظام»، لا
     «اتبعه لحظة الفتح». */
  if (dark && dark.addEventListener) {
    dark.addEventListener("change", function () {
      if (look.scheme === "auto") apply();
    });
  }

  /* ------------------------------------------------------------------------
     ما بعد أول رسم: الأزرار. لا شيء تحت هذا السطر يلمس المظهر قبل أن يُنقر.
     ------------------------------------------------------------------------ */
  document.addEventListener("DOMContentLoaded", function () {
    var themer = document.querySelector(".themer");
    var veil = document.querySelector(".themer-veil");

    function set(name, value) {
      if (!ALLOWED[name] || ALLOWED[name].indexOf(value) === -1) return;
      look[name] = value;
      apply();
      write();
      mark();
    }

    /* المختار يُعلَن بـ aria-pressed لا بصنفٍ: ما يراه المبصر وما يقوله قارئ
       الشاشة شيءٌ واحد، ولا يفترقان عند تعديلٍ لاحق. */
    function mark() {
      var options = document.querySelectorAll("[data-look]");
      for (var i = 0; i < options.length; i++) {
        var button = options[i];
        var name = button.getAttribute("data-look");
        var on = look[name] === button.getAttribute("data-value");
        button.setAttribute("aria-pressed", on ? "true" : "false");
      }
      var toggle = document.querySelector("[data-nav-toggle]");
      if (toggle) toggle.setAttribute("aria-expanded", look.nav === "full" ? "true" : "false");
    }

    function open(yes) {
      if (!themer) return;
      themer.setAttribute("aria-hidden", yes ? "false" : "true");
      if (veil) veil.setAttribute("aria-hidden", yes ? "false" : "true");
      if (yes) {
        var first = themer.querySelector("button");
        if (first) first.focus();
      }
    }

    document.addEventListener("click", function (event) {
      var hit = function (selector) {
        return event.target.closest ? event.target.closest(selector) : null;
      };

      var option = hit("[data-look]");
      if (option) {
        set(option.getAttribute("data-look"), option.getAttribute("data-value"));
        return;
      }

      if (hit("[data-nav-toggle]")) {
        /* الشاشة الضيّقة تُخفي ولا تطوي: الشريط هناك درجٌ منزلق، ولا معنى
           لحالةٍ «مطوية» فيه. (والاستعلام هو `narrow` أعلاه لا نسخةٌ ثانية:
           سلسلتان تفترقان يوم تتغيّر نقطة الانكسار.) */
        var small = narrow && narrow.matches;
        set("nav", look.nav === "full" ? (small ? "off" : "mini") : "full");
        return;
      }

      /* النقر على الحجاب: `::before` عنصرٌ زائف لا يظهر في `event.target`،
         فالهدف هو `.shell` نفسها — وذلك يقع فقط حين يكون الحجاب فوق كل شيء،
         أي والدرج مفتوحٌ على شاشةٍ ضيّقة. */
      if (
        look.nav === "full" &&
        narrow && narrow.matches &&
        event.target.classList && event.target.classList.contains("shell")
      ) {
        set("nav", "off");
        return;
      }

      if (hit("[data-themer-open]")) { open(true); return; }
      if (hit("[data-themer-close]") || event.target === veil) { open(false); return; }

      if (hit("[data-look-reset]")) {
        for (var name in DEFAULTS) look[name] = DEFAULTS[name];
        apply();
        write();
        mark();
      }
    });

    /* Escape يغلق الدرج — والزرّ الذي فتحه يبقى في مكانه فلا يضيع التركيز. */
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") open(false);
    });

    mark();
    counters();
  });

  /* ------------------------------------------------------------------------
     الأرقام تعدّ إلى قيمتها عند أول رسم.
     ------------------------------------------------------------------------
     الشرطان اللذان يجعلانها حركةً لا عطلاً:

     1. **النصّ النهائي موجودٌ في الصفحة قبل أن تبدأ.** الخادم يرسمه، وهذا
        الكود يستبدله ثم يعيده حرفياً. فمن أطفأ الجافاسكربت، أو قرأ بقارئ شاشة
        يأخذ لقطةً من الشجرة قبل انتهاء العدّ، يرى الرقم كاملاً لا صفراً.
     2. **ما لا يُقرأ رقماً لا يُلمَس.** «9.63M» و«12 مزاداً» و«—» تُترك كما
        هي: عدٌّ يفكّ تنسيق المبلغ ثم يعيد تركيبه خطأً يكذب على قارئه، وبطاقةُ
        مالٍ تكذب أسوأ من بطاقةٍ لا تتحرّك.

     و prefers-reduced-motion تُطفئها كلّها — كما في آخر app.css. */
  function counters() {
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || look.motion === "off") return;

    var values = document.querySelectorAll(".stat__value");
    for (var i = 0; i < values.length; i++) count(values[i]);
  }

  function count(node) {
    var text = node.textContent.trim();
    /* أرقامٌ وفواصل آلاف لا غير — بلا لواحق ولا كسور ولا حروف. */
    if (!/^\d{1,3}(,\d{3})*$/.test(text)) return;

    var target = parseInt(text.replace(/,/g, ""), 10);
    if (!isFinite(target) || target < 2) return;

    var started = null;
    var span = 700;

    function step(now) {
      if (started === null) started = now;
      var portion = Math.min((now - started) / span, 1);
      /* تباطؤٌ في النهاية: العدّ الخطّي يصل فيقف فجأةً، وهذا يستقرّ. */
      var eased = 1 - Math.pow(1 - portion, 3);
      node.textContent = Math.round(target * eased).toLocaleString("en-US");
      if (portion < 1) {
        window.requestAnimationFrame(step);
      } else {
        node.textContent = text;   /* النصّ الأصلي حرفياً، لا نتيجةَ تنسيقٍ ثانٍ */
      }
    }

    window.requestAnimationFrame(step);
  }
})();
