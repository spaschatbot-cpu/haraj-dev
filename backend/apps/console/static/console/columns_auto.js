/* تخصيصُ أعمدةِ أيِّ جدولٍ في اللوحة — بلا تسجيلٍ ولا تعديلِ قالب. T964.
   ========================================================================

   ## لماذا آليّةٌ عامّة لا تسجيلُ جدولٍ جدول

   في اللوحة تسعٌ وعشرون شاشةً ذاتَ جدول، وقِيس أن `data-col` موجودٌ في
   **واحدةٍ منها فقط**. والآليّةُ المسجَّلة (`columns.py` + `_columns.html`)
   تتطلّب لكلّ جدول: صفّاً في السجلّ، ووسمَ كلّ `<th>` و`<td>` بمفتاحه،
   وثلاثةَ متغيّراتٍ في العرض، وشمولَ المكوّن. أي نحو مئتَي تعديلٍ يدويٍّ
   موزَّعةٍ على تسعة قوالبَ مختلفةِ الشكل — وكلُّ واحدٍ منها فرصةُ خطأٍ صامت
   (خليّةٌ تُنسى فينزاح عمودٌ عند الإخفاء).

   وطلبُ المالك (٢١ سبتمبر ٢٠٢٦): «كل جدول فيه أكتر من ١٠ أعمدة». فالعموميّةُ
   هي الجواب: هذا الملفُّ يقرأ الجدولَ نفسَه — رؤوسَه وصفوفَه — ويبني المُنتقي
   منه.

   ## والإخفاءُ بالموضع لا بالمفتاح

   `<col>` لا يقبل `display:none` في المتصفّحات (حيلةٌ تُكتب كثيراً ولا تعمل)،
   فالإخفاءُ بسمة `hidden` على `<th>` و`<td>` في **الموضع نفسِه** من كلّ صفّ.

   والمفتاحُ المحفوظ من `data-col` إن وُجد، وإلا فمن **نصّ الرأس** لا من رقمه:
   رقمُ العمود يتغيّر بإضافة عمودٍ قبله فينزاح تخصيصُ الموظّف إلى عمودٍ آخر،
   والنصُّ يبقى ما بقي العنوان.

   ## وما لا يمسّه

   * جدولٌ له مُنتقٍ أصلاً (`[data-columns-open]` أو `[data-column]`) يُترَك —
     مُنتقيان فوق جدولٍ واحدٍ أسوأُ من واحد.
   * جدولٌ أعمدتُه قليلة: لا يفيض، وزرٌّ فوقه ضجيج.
   * العمودُ الأوّل والأخير **يُقفَلان**: الأوّلُ هويّةُ الصفّ والأخيرُ أفعالُه،
     وإخفاءُ أيٍّ منهما تعطيلٌ لا تخصيص — وهي قاعدةُ `columns.py` نفسُها.

   ## والبذرةُ من DOM

   ما وصل من الخادم بسمة `hidden` يبقى مخفيّاً حتى يُظهره الموظّف. وهذا ما
   يجعل «مخفيٌّ افتراضاً» في `columns.py` يعمل بدل أن يُمحى في أوّل إطار —
   وهو العطلُ الذي كلّف T962 قياساً كاملاً. */
(function () {
  "use strict";

  /** أقلُّ عددِ أعمدةٍ يستحقّ زرّاً. دونه لا يفيض الجدولُ ولا يُزدحم. */
  var MIN_COLUMNS = 9;

  var STORE = "haraj.console.cols.";

  function textKey(th) {
    var explicit = th.getAttribute("data-col");
    if (explicit) return explicit;
    var label = (th.textContent || "").replace(/\s+/g, " ").trim();
    return label ? "t:" + label : "";
  }

  function storeKeyFor(index) {
    // المسارُ يميّز الشاشة، والرقمُ يميّز جدولاً ثانياً فيها. ولا `search`:
    // تخصيصُ الأعمدة لا يتغيّر بتغيّر المرشِّح.
    return STORE + location.pathname + "#" + index;
  }

  function read(key) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) || [] : null;
    } catch (e) {
      // التصفّحُ الخاصّ يرمي عند القراءة نفسِها في بعض المتصفّحات.
      return null;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* ممتلئٌ أو محظور — الاختيارُ يعمل هذه الجلسة ولا يُحفَظ. */
    }
  }

  /** صفوفُ الجدول التي تحمل عدداً كاملاً من الخلايا.
   *
   *  صفُّ «لا نتائج» خليّةٌ واحدةٌ بـ`colspan`، وإخفاءُ موضعٍ فيه يُخفي
   *  الرسالةَ كلَّها. فيُتخطّى. */
  function fullRows(table, count) {
    var rows = table.querySelectorAll("tr");
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].children.length === count) out.push(rows[i]);
    }
    return out;
  }

  function setup(table, index) {
    var head = table.tHead && table.tHead.rows.length ? table.tHead.rows[0] : null;
    if (!head) return;

    var heads = [].slice.call(head.children);
    if (heads.length < MIN_COLUMNS) return;

    // مُنتقٍ قائمٌ في الصفحة: لا يُضاف ثانٍ.
    if (document.querySelector("[data-columns-open], [data-column]")) return;

    var keys = heads.map(textKey);
    var rows = fullRows(table, heads.length);
    var storeKey = storeKeyFor(index);

    function apply(hidden) {
      for (var c = 0; c < heads.length; c++) {
        var off = hidden.indexOf(keys[c]) !== -1;
        for (var r = 0; r < rows.length; r++) {
          if (rows[r].children[c]) rows[r].children[c].hidden = off;
        }
      }
    }

    // **البذرةُ من DOM حين لا تخصيصَ محفوظ** — لا `[]`. انظر رأس الملفّ.
    var saved = read(storeKey);
    var hidden = saved;
    if (hidden === null) {
      hidden = [];
      for (var i = 0; i < heads.length; i++) {
        if (heads[i].hidden) hidden.push(keys[i]);
      }
    }
    apply(hidden);

    // الأوّلُ والأخيرُ مقفولان — هويّةُ الصفّ وأفعالُه.
    var locked = {};
    locked[keys[0]] = true;
    locked[keys[heads.length - 1]] = true;

    /* **وعمودٌ له أن يقول «لا تُخفِني تلقائيّاً».** T965.
    
       التقليصُ التلقائيُّ يختار **الأعرضَ**، وهي قاعدةٌ صحيحةٌ في الغالب:
       العمودُ الواسعُ نصٌّ حرٌّ يُقرأ عند الحاجة. لكنّها تنقلب في شاشةٍ
       عمودُها الواسعُ هو موضوعُها — «منصّة الملّاك» فتحت أوّلَ مرّةٍ فأخفت
       **«أعلى عرض» و«شامل الضريبة» و«أعلى مزايد»**، أي الثلاثةَ التي يُفتح
       لأجلها الجدول، وأبقت «سنة الصنع» و«التسويق». قِيس: خمسةٌ مخفيّةٌ من
       خمسةَ عشر، وفيها الثلاثة.
    
       و`data-keep` **ليس قفلاً**: العمودُ يبقى في المنتقي ويخفيه الموظّفُ
       متى شاء. هو يقول لآليّة التقليص وحدَها: ابدأ من غيري. */
    var keep = {};
    for (var k = 0; k < heads.length; k++) {
      if (heads[k].hasAttribute("data-keep")) keep[keys[k]] = true;
    }

    /* **ويُقلَّص حتى يتّسع — مرّةً واحدةً، ولمن لم يخصّص.** T964.

       طلبُ المالك: «عايز الداتا تتعرض بدون الحاجة للاسكرول يمين وشمال».
       وزرُّ التخصيص وحدَه يُعطي القدرةَ ولا يُعطي النتيجة: من يفتح الشاشةَ
       أوّلَ مرّةٍ يجدها تفيض، ولا يعرف أن الحلَّ خلف زرّ.

       فيُخفى **الأعرضُ فالأعرض** حتى يتّسع الجدولُ في حاويته. والأعرضُ لا
       الأخير: العمودُ الواسعُ نصٌّ حرٌّ غالباً (ملاحظة، سبب، اسمُ شركة)،
       وهو أقلُّ ما يُقرأ في مسحٍ سريعٍ للصفوف وأكثرُ ما يأكل العرض.

       **وسقفُ الثلث**: جدولٌ يُخفى نصفُه لم يعد جدولَه. فإن لم يتّسع بثلث
       أعمدته يبقى التمريرُ — وهو أصدقُ من شاشةٍ فقدت معناها.

       ويُكتب الناتجُ في التخزين: لو تُرك محسوباً في كلّ فتحةٍ لتغيّرت
       الأعمدةُ الظاهرةُ مع تغيّر البيانات — صفحةٌ فيها اسمٌ طويلٌ تُخفي
       عموداً وصفحةٌ بعدها تُظهره، والموظّفُ يظنّ الشاشةَ تتبدّل تحت يده. */
    if (saved === null) {
      var box = table.closest(".scroller") || table.parentElement;
      var budget = Math.floor(heads.length / 3);
      while (budget-- > 0 && box.scrollWidth - box.clientWidth > 1) {
        var widest = -1;
        var widestSize = 0;
        for (var w = 0; w < heads.length; w++) {
          if (locked[keys[w]] || keep[keys[w]] || !keys[w] || heads[w].hidden) continue;
          var size = heads[w].getBoundingClientRect().width;
          if (size > widestSize) { widestSize = size; widest = w; }
        }
        if (widest === -1) break;
        hidden.push(keys[widest]);
        apply(hidden);
      }
      if (hidden.length) write(storeKey, hidden);
    }

    var modal = document.createElement("dialog");
    modal.className = "modal columns-modal";
    var list = document.createElement("ul");
    list.className = "columns-list";

    heads.forEach(function (th, i) {
      var key = keys[i];
      if (!key || locked[key]) return;
      var row = document.createElement("li");
      row.className = "columns-list__row";
      var label = document.createElement("label");
      label.className = "columns-list__label";
      var box = document.createElement("input");
      box.type = "checkbox";
      box.checked = hidden.indexOf(key) === -1;
      box.setAttribute("data-key", key);
      var span = document.createElement("span");
      span.textContent = (th.textContent || "").replace(/\s+/g, " ").trim() || "عمود " + (i + 1);
      label.appendChild(box);
      label.appendChild(span);
      row.appendChild(label);
      list.appendChild(row);
    });

    var head2 = document.createElement("header");
    head2.className = "columns-modal__head";
    head2.innerHTML = "<h2>الأعمدة الظاهرة</h2><p>أخفِ ما لا تحتاجه. يُحفظ على هذا الجهاز.</p>";

    var foot = document.createElement("footer");
    foot.className = "columns-modal__foot";
    var done = document.createElement("button");
    done.type = "button";
    done.className = "btn-primary";
    done.textContent = "تمّ";
    foot.appendChild(done);

    modal.appendChild(head2);
    modal.appendChild(list);
    modal.appendChild(foot);
    document.body.appendChild(modal);

    // **الأثرُ فوريٌّ عند كلّ خانة، لا عند «احفظ»**: من يُخفي عموداً يريد أن
    // يرى الجدولَ بعده ليقرّر التالي.
    list.addEventListener("change", function (event) {
      var box = event.target;
      if (!box || box.type !== "checkbox") return;
      var key = box.getAttribute("data-key");
      var at = hidden.indexOf(key);
      if (box.checked && at !== -1) hidden.splice(at, 1);
      if (!box.checked && at === -1) hidden.push(key);
      apply(hidden);
      write(storeKey, hidden);
    });
    done.addEventListener("click", function () { modal.close(); });

    var button = document.createElement("button");
    button.type = "button";
    button.className = "btn-sm";
    button.textContent = "تخصيص الأعمدة";
    button.setAttribute("aria-haspopup", "dialog");
    button.addEventListener("click", function () {
      if (modal.showModal) modal.showModal();
    });

    // مكانُ الزرّ: شريطُ أدوات الجدول إن وُجد، وإلا فوق الجدول مباشرةً.
    var bar = table.closest(".scroller");
    bar = bar ? bar.previousElementSibling : null;
    var slot = bar && bar.querySelector ? bar.querySelector(".table-bar__actions") : null;
    if (slot) {
      slot.insertBefore(button, slot.firstChild);
    } else {
      var holder = document.createElement("div");
      holder.className = "cols-auto-bar";
      holder.appendChild(button);
      var box2 = table.closest(".scroller") || table;
      box2.parentNode.insertBefore(holder, box2);
    }
  }

  function start() {
    var tables = document.querySelectorAll("main table");
    for (var i = 0; i < tables.length; i++) setup(tables[i], i);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
