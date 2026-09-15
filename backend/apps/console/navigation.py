"""Every page in the console, declared once. T802.

The sidebar and the guard on each page read **the same rows**. That is the whole
design, and it is the answer to a specific v1 failure: there, the menu was one
list and the access rules were another, so a page added to the second and
forgotten in the first was invisible to the people who were allowed to use it —
and a page added to the first and forgotten in the second was a link everybody
could see and nobody could open. Both happened.

So a page here is a :class:`Page` row: a url name, a label, and the one
capability that both shows it in the sidebar and lets it be opened. Adding a
screen means adding a row; there is no second place to forget.

`test_navigation.py` proves the equivalence the hard way rather than by reading
this docstring: it signs in as each role, walks every url in the registry, and
asserts that the set of pages that answer 200 is exactly the set the sidebar
offered. A page guarded by one capability and listed under another fails it.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.core.permissions import Capability, capabilities_of


@dataclass(frozen=True)
class Page:
    """One console screen: where it is, what it is called, who may open it."""

    #: Django url name, namespaced. Resolved with `{% url %}` and never written
    #: out as a path — see `ops/checks/console_urls_are_named.py` (T804).
    url_name: str

    label: str

    #: The single capability that both reveals this page in the sidebar and
    #: admits a caller to it. One field, because two would be the v1 bug.
    capability: str

    #: Which group the sidebar shows it under. Presentation only; it never
    #: affects access.
    section: str

    #: سطرٌ يقول ما تفعله هذه الشاشة — تقرأه الصفحةُ الرئيسية وحدها.
    #:
    #: الشريط الجانبي يعرض الأسماء، فرئيسيةٌ تعرض الأسماء نفسها تحت العناوين
    #: نفسها تكون نسخةً حرفية مما يراه القارئ بجانبها في اللحظة ذاتها. الاسم
    #: يقول أين تذهب، وهذا السطر يقول لماذا — وهو الفرق الوحيد الذي يجعل
    #: للصفحة سبب وجود.
    #:
    #: فارغٌ لصفحات التفصيل: لا تُعرض في شبكةٍ ولا في شريط، فلا أحد يقرأه.
    blurb: str = ""

    #: اسمُ أيقونتها في :mod:`apps.console.icons` — لا مسارُها ولا رمزُها.
    #:
    #: كانت رمزاً نصّياً (`🔨`) في T833، وحُجّتها أن الخطّ قد لا يصل. والثمن
    #: أن نظام التشغيل هو الذي يرسمه: ملوّناً بأسلوبٍ لا يشبه اللوحة، ومختلفاً
    #: بين ويندوز وأندرويد — ستّة عشر رسماً لستّة عشر أسلوباً (T837).
    #:
    #: و`<svg>` مضمَّنٌ في الصفحة لا يُحمَّل ولا «قد لا يصل»، ويرث
    #: `currentColor` فيتلوّن مع القسم الحالي ومع اللون الأساسي المختار.
    #:
    #: **اسمٌ لا مسار**: المسار سلسلةٌ من مئة حرف، وصفٌّ في هذا السجلّ يجب أن
    #: يُقرأ. و`test_icons.py` يمسك الاسم الخطأ فلا يُرسَم مربّعٌ فارغ.
    #:
    #: وهي تزيينٌ صراحةً: القالب يضع `aria-hidden` عليها، والاسمُ الكامل يبقى
    #: في `data-label` و`title` — فمن يقرأ بقارئ شاشة يسمع الاسم، حتى والشريط
    #: مطويّ.
    icon: str = ""

    @property
    def icon_path(self) -> str:
        """بيانات `d` لأيقونتها. فارغةٌ تعني «لا تُرسَم»، لا «مربّع فارغ»."""
        from .icons import path_of

        return path_of(self.icon)

    #: الشاشةُ التي يعود إليها زرُّ «رجوع» — **اسمُ مسارٍ بلا وسائط**. T864
    #:
    #: صفحاتُ التفصيل تُفتح من قائمةٍ ولا مدخلَ لها في الشريط، فالخروجُ منها
    #: كان بسهم المتصفّح وحده — و`history.back()` بعد `POST` يعيد إرسالَ
    #: الاستمارة أو يقع على صفحةٍ من موقعٍ آخر. فالوجهةُ **مصرَّحة** هنا.
    #:
    #: وبلا وسائط عمداً: أبٌ يحتاج `pk` يعني أن كل قالبٍ يبني الرابط بيده،
    #: وذاك ما يرفضه `console_urls_are_named`. والآباءُ كلُّهم قوائم.
    parent: str = ""


@dataclass(frozen=True)
class Section:
    key: str
    label: str


@dataclass(frozen=True)
class Planned:
    """مدخلٌ في قائمة v1 لم تُبنَ شاشته بعد — يُعرَض ولا يُفتَح. T831.

    لماذا يُعرَض أصلاً
    ==================
    القاعدة السابقة كانت عكس هذا بالحرف: «عنوانٌ بلا صفحاتٍ تحته وعدٌ بصفحةٍ
    لا يستطيع القارئ فتحها»، ولذلك كان `sidebar_for` يُسقط القسم الفارغ. وكانت
    القاعدة صحيحةً لقارئٍ **لا يعرف ما ينقص**.

    والمالك ليس ذلك القارئ. هو يعمل على قائمة v1 كل يوم، ويعرف الواحدة
    والستّين مدخلاً فيها بأسمائها؛ فحين يرى ستّة عشر لا يقرأ «اللوحة أصغر» بل
    **«اللوحة فقدت صفحاتي»**. وقال ذلك حرفياً: «الصفحات مظهرتش كلها في السايد
    بار، عوزه نفس اللي بعتهولك».

    فالغياب الصامت هو الوعد الكاذب هنا، لا الحضور. والمدخل المعروض يقول ثلاثة
    أشياء لا يقولها الفراغ: أن الشاشة معروفة، وأن مكانها محجوز، وأنها لم تُبنَ
    بعد.

    ولماذا نوعٌ مستقلٌّ لا حقلٌ في :class:`Page`
    =============================================
    لأن `PAGES` تعني «مبنيّةٌ ومحروسة»، ويقرأها ثمانية مواضع تفترض ذلك:
    `capability_for` و`pages_for` و`test_navigation` (يفتح كل صفٍّ فيها ويطلب
    ٢٠٠) و`every_capability_guards_something`. وصفٌّ بلا `url_name` بينها
    كان سيُمرَّر إلى `reverse()` فيرمي، أو — وهو الأسوأ — يُستثنى بشرطٍ في كل
    موضعٍ من الثمانية، فيصير الشرط هو المكان الجديد الذي يُنسى فيه.

    ونوعان مختلفان لا يختلطان: لا `url_name` هنا **بنية الصنف نفسها**، فلا
    رابط يُرسَم ولا حارس يُسأل ولا اختبارٌ يفتحها. والانتقال من هنا إلى هناك
    حذفُ صفٍّ وإضافةُ آخر — و`test_navigation` يرفض بقاءهما معاً.
    """

    label: str
    section: str

    #: مسارها في v1، كما لصقه المالك. يُعرض في `title` ولا يُرسَم رابطاً:
    #: هو **مرجعٌ لمن يبنيها** لا وجهةٌ يُرسَل إليها موظّف — نظامان مفتوحان
    #: في تبويبين يعملان على نفس المال أخطرُ من شاشةٍ ناقصة.
    v1_path: str = ""

    #: `⛔` حين لا يكون البناء نقلاً: الشاشة موجودةٌ في v1 وقرارُها أن تُبنى
    #: **بشكلٍ آخر** (نظام الكروت، صلاحيات الأدوار). القالب يقولها.
    rebuilt: bool = False

    #: رسمٌ واحدٌ لكلّها عمداً: الأيقونة في الشريط تميّز الوجهات بعضها من بعض،
    #: والمدخلات هنا **ليست وجهات**. ورسمُ سيّارةٍ بجوار «كتالوج السيارات» ثم
    #: منعُ فتحها يجعل الصفَّ يبدو جاهزاً وهو ليس كذلك؛ والدائرة المجوّفة تقول
    #: «مكانٌ محجوز» بلا ادّعاء.
    icon: str = "dot"

    @property
    def icon_path(self) -> str:
        from .icons import path_of

        return path_of(self.icon)


#: أقسام الشريط، **بأسماء v1 نفسها وترتيبها** (T837).
#:
#: كانت أربعةً من اختراعنا — «التشغيل اليومي» و«المال» و«التشخيص» و«الإدارة» —
#: وهي تسميةٌ معقولة ولا أحد يعرفها. والمالك وموظّفوه يعملون على قائمة v1 كل
#: يوم منذ سنين: «إدارة المزادات» و«المحفظة» و«شريك التسويق» أسماءٌ في رؤوسهم
#: لا في ملفّ. وتحويلٌ يُعيد ترتيب المنيو **مع** تغيير كل شاشة هو تحويلان في
#: وقتٍ واحد، وأحدُهما بلا مقابل.
#:
#: وكلُّها تظهر اليوم: `PLANNED` تملأ ما لم يُبنَ بعد (T831)، فلا قسمَ فارغاً
#: يُسقَط. وكان `sidebar_for` يُسقطه، والحجّة أن «عنواناً بلا صفحاتٍ تحته وعدٌ
#: بصفحةٍ لا يستطيع القارئ فتحها» — وهي حجّةٌ انقلبت حين تبيّن أن القارئ يعرف
#: القائمة عن ظهر قلب: انظر :class:`Planned`.
#: جذرُ اللوحة — إليه يعود كلُّ ما لا أبَ له. T864
HOME = "console:home"


SECTIONS: tuple[Section, ...] = (
    # في v1 الجذرُ نفسه هو «لوحة التحليلات والإحصائيات»، و«الرئيسية» رابطٌ
    # فوق كل الأقسام لا داخل واحدٍ منها. فهذا القسم أوّلها ويحمل الاثنتين.
    Section("home", "الرئيسية"),
    Section("members", "إدارة الأعضاء"),
    Section("auctions", "إدارة المزادات"),
    Section("decisions", "قرارات المزايدات"),
    Section("finance", "المالية والمدفوعات"),
    Section("wallet", "المحفظة"),
    Section("invoices", "الفواتير"),
    Section("reports", "التقارير والتحليلات"),
    Section("support", "الإشعارات والدعم"),
    Section("system", "النظام والصلاحيات"),
    Section("partner", "شريك التسويق"),
)


#: The console, in full. A screen that is not here does not exist as far as the
#: sidebar or the guards are concerned — which is deliberate: an unlisted page
#: reachable by url is exactly the shape of an accidental leak.
PAGES: tuple[Page, ...] = (
    # ---- الرئيسية — بترتيب v1 وأسمائه --------------------------------------
    #: الجذر هو اللوحة نفسها، كما هو في v1 («لوحة التحليلات والإحصائيات»).
    #: وكانت هنا صفحتان: «الرئيسية» شبكةَ كروتٍ تشرح الشاشات، و«لوحة
    #: التحليلات» تحتها. والشبكة كانت تقول ما يقوله الشريط الجانبي بجوارها،
    #: وسطرُ الشرح انتقل إلى `title` الرابط في الشريط — فبقيت صفحةٌ تُفتح
    #: أولاً ولا تحمل جواباً، ويمرّ عليها الموظّف كلَّ صباح إلى الصفحة التالية.
    Page(
        "console:home",
        "الرئيسية",
        Capability.CONSOLE_ACCESS,
        "home",
        "أرقام المنصّة، وكلٌّ منها بابٌ إلى الشاشة التي تتصرّف فيه.",
        "chart",
    ),
    # ---- إدارة الأعضاء — بترتيب v1 وأسمائه ---------------------------------
    Page(
        "console:customers",
        "إدارة المستخدمين",
        Capability.USERS_VIEW,
        "members",
        "العملاء والشركات وبياناتهم الموثّقة.",
        "users",
    ),
    Page(
        "console:user-bids",
        "تقرير مزايدات مستخدم",
        Capability.USERS_VIEW,
        "members",
        "كل ما زايد به شخصٌ واحد وما فاز به — ولا تفتح على أصفارٍ قبل أن تُسأل.",
        "person-search",
    ),
    Page(
        "console:admins",
        "إدارة المشرفين",
        Capability.STAFF_GRANT,
        "members",
        "من يفتح اللوحة، بأي دور، ومتى دخل آخر مرّة — واستثناءاته فوق دوره.",
        "shield",
    ),
    # ---- إدارة المزادات — بترتيب v1 وأسمائه --------------------------------
    Page(
        "console:auctions",
        "قائمة المزادات",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "المزاد الأسبوعي وحالته، وجدولته وبدؤه وإنهاؤه.",
        "award",
    ),
    Page(
        "console:vehicle-search",
        "بحث عن سيارة",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "خانةٌ لكل عمود — لوحةٌ أو شاصي أو اسم أو لوت، ولا تفتح على القائمة كلّها.",
        "search-car",
    ),
    Page(
        "console:auctions-manage",
        "إدارة مزاد + سياراته",
        Capability.AUCTIONS_MANAGE,
        "auctions",
        "اختر مزاداً لتفتح سياراته أو تعديله أو مزايداته — مدخلٌ واحد لا ثلاثة.",
        "folder",
    ),
    Page(
        "console:auctions-quick-edit",
        "تعديل سريع للعدادات",
        Capability.AUCTIONS_MANAGE,
        "auctions",
        "جدولُ عدّاداتِ مزادٍ واحد — وما تغيّر وحده يُكتب، ولكلٍّ قيدُه.",
        "gauge-edit",
    ),
    Page(
        "console:vehicle-catalog",
        "كتالوج السيارات",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "كل مركبة بمواصفاتها وصورها ومزادها — بفلاتر التواريخ الأربعة.",
        "grid",
    ),
    Page(
        "console:auction-archive",
        "أرشيف المزادات",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "المزادات المنتهية، وما بيع في كلٍّ منها وبكم.",
        "archive",
    ),
    Page(
        "console:after-sales",
        "ما بعد البيع",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "ما بيع ولمن — وحالةُ فاتورته مشتقّةً من دفعاتها لا من كلمة أودو.",
        "handshake",
    ),
    Page(
        "console:vehicle-exit",
        "الخروج ونقل الملكية",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "ما سُدِّد ولم يخرج بعد، وما خرج — ولا سيارةَ في الطابور بلا مالها.",
        "exit",
    ),
    Page(
        "console:ended-decisions",
        "القرارات المنتهية",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "ما حُسم فيه قرار — والمرفوضُ فيه كالمقبول، فالسؤال «ماذا قرّرنا».",
        "stamp",
    ),
    # ‏**خارج الشريط بقرار المالكة (١٥ سبتمبر ٢٠٢٦)، ولم تُحذف.** القسمُ الفارغ
    # يُخرجها من `sidebar_for` ومن شبكة الرئيسية، و`parent` يُبقي لها زرَّ رجوع.
    # والشاشةُ ومسارُها وحارسُها كما هي: من يملك الرابط يفتحها، ومن لا يملك
    # `auctions.manage` يُردّ كما كان. إعادتُها سطرٌ واحد: `"auctions"` مكان
    # `""` وحذفُ `parent`.
    Page(
        "console:auctions-bulk",
        "عمليات مجمعة",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:vehicles",
        "المركبات",
        Capability.AUCTIONS_VIEW,
        "auctions",
        "كل مركبة وحالتها ولوتها وسعر وقوفها.",
        "car",
    ),
    # خارج الشريط بقرار المالكة — انظر «عمليات مجمعة» أعلاه.
    Page(
        "console:vehicles-import",
        "استيراد المركبات",
        Capability.AUCTIONS_IMPORT,
        "",
        parent="console:vehicles",
    ),
    # ---- قرارات المزايدات — بترتيب v1 وأسمائه ------------------------------
    Page(
        "console:reminders",
        "تذكيرات المزادات",
        Capability.AUCTIONS_MANAGE,
        "support",
        "أيُّ مزادٍ حان تذكيرُه وكم شخصاً سيصله — والإدراجُ بضغطةِ إنسان.",
        # كان `bell` وهو نفسُه على «سجل الإشعارات» في القسم نفسه. والتذكيرُ
        # موعدٌ يحين، والسجلُّ ما أُرسل — فالروزنامةُ والساعة أدقّ، والجرسُ
        # يبقى للسجلّ. (وفي الشريط المطويّ لا يبقى إلا الرسم.)
        "calendar-clock",
    ),
    Page(
        "console:reminder-send",
        "إدراج تذكير",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:reminders",
    ),
    Page(
        "console:live-bids",
        "مزايدات المزاد الجاري",
        Capability.AUCTIONS_VIEW,
        "decisions",
        "ما يُزايَد عليه الآن — أعلى مبلغ وعدد المزايدين، والمزادُ مفتوح.",
        # كان `gauge` وهو نفسُه على «احصائيات المزاد النشط». وهذه **مراقبة**
        # لما يجري الآن، وتلك عدّاداتُ إحصاء — فالعينُ هنا والعدّادُ هناك.
        "eye",
    ),
    # خارج الشريط بقرار المالكة — انظر «عمليات مجمعة» أعلاه. وتبقى أباً
    # لـ«مزايدات المركبة» فزرُّ الرجوع منها لا ينكسر.
    Page(
        "console:vehicle-bids",
        "مزايدات السيارات",
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:live-bids",
    ),
    Page(
        "console:vehicle-bid-list",
        "مزايدات المركبة",
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:vehicle-bids",
    ),
    Page(
        "console:accepted-bids",
        "المزايدات المقبولة",
        Capability.AUCTIONS_VIEW,
        "decisions",
        "كل مركبةٍ رست ومن أخذها وبكم — وضريبتُها من فاتورتها لا من حسابٍ ثانٍ.",
        "gavel",
    ),
    Page(
        "console:accepted-summary",
        "ملخّص المقبولة",
        Capability.AUCTIONS_VIEW,
        "decisions",
        "إجمالي ما رسا وما فُوتِر منه — والفرقُ بينهما عملٌ ينتظر.",
        "sum",
    ),
    # ---- المالية والمدفوعات — بترتيب v1 وأسمائه ----------------------------
    Page(
        "console:payment-create",
        "إنشاء دفعة",
        Capability.PAYMENTS_RECORD,
        "finance",
        "قيدُ سدادٍ نقديٍّ على فاتورة — بمرجعٍ يمنع القيد مرّتين وسببٍ إجباريّ.",
        "invoice-plus",
    ),
    Page(
        "console:payments",
        "إدارة المدفوعات",
        Capability.INVOICES_VIEW,
        "finance",
        "كل محاولة سداد وما صارت إليه — والفاشلة معها.",
        "card",
    ),
    Page(
        "console:refunds",
        "الاستردادات",
        Capability.MONEY_VIEW,
        "finance",
        "كم طلباً وفي أي حالة — مصدرٌ واحد بدل ثلاثة أرقامٍ لشيءٍ واحد.",
        "undo",
    ),
    # T921. `packages.manage` لا `money.act`: تلك تحرّك مالاً **موجوداً** في
    # الدفتر، وهذه تغيّر **الشرطَ** الذي يقرّر من يزايد أصلاً — وحاملُ
    # `money.act` اليوم دورُ «المالية» كلُّه.
    Page(
        "console:packages",
        "الباقات",
        Capability.PACKAGES_MANAGE,
        "finance",
        "عتبةُ التأمين التي تفتح المزايدة وحصّةُ المزادات — وتغييرُ السعر بسببٍ وقيد.",
        "package",
    ),
    # ---- المحفظة — بترتيب v1 وأسمائه ---------------------------------------
    Page(
        "console:money-health",
        "صحّة المحفظة",
        Capability.DIAGNOSTICS_VIEW,
        "wallet",
        "أربعة فحوص مستقلّة على الدفتر، وكل خلاف تقوله بصراحة.",
        "pulse",
    ),
    Page(
        "console:why-no-bid",
        "لماذا لا يستطيع العميل المزايدة؟",
        Capability.DIAGNOSTICS_VIEW,
        "wallet",
        "عميلٌ ومركبة، والجواب: أي شرطٍ بالضبط منعه.",
        "help",
    ),
    Page(
        "console:wallet-credit",
        "شحن يدوي",
        Capability.MONEY_ACT,
        "wallet",
        "شحنٌ بمرجعٍ وسبب — والمرجع يمنع التقييد مرّتين مهما ضُغط الزرّ.",
        "plus-wallet",
    ),
    Page(
        "console:bank-topups",
        "طلبات الشحن البنكي",
        Capability.MONEY_VIEW,
        "wallet",
        "طابورُ «إدارة الطلبات»: تُطابَق بكشف البنك وتُعتمد بما وصل فعلاً لا بما ادُّعي.",
        # كان `receipt` وهو نفسُه على «سجل الدفعات» في قسم الشريك. وهذه
        # **طلبٌ بنكيٌّ ينتظر**، وتلك إيصالُ ما دُفع — فالمبنى هنا والإيصالُ هناك.
        "bank",
    ),
    Page(
        "console:money-ledger",
        "سجل المحفظة",
        Capability.MONEY_VIEW,
        "wallet",
        "كل ريال دخل أو خرج أو حُجز — للقراءة، والحركة تُصنع من أفعال المال.",
        "book",
    ),
    Page(
        "console:insurance-report",
        "تقرير المحفظة",
        Capability.MONEY_VIEW,
        "wallet",
        "من دفع تأميناً وكم — مجموعاً من الدفتر لا من عمودٍ مخزَّن.",
        "wallet",
    ),
    Page(
        "console:direct-deduct",
        "خصم مباشر من التأمين",
        Capability.MONEY_ACT,
        "wallet",
        "ما يمكن أن يخرج من رصيد العميل مسمّىً بمقداره — لا خانةَ مبلغٍ حرّة.",
        "minus-wallet",
    ),
    # ---- الفواتير — بترتيب v1 وأسمائه --------------------------------------
    Page(
        "console:invoices",
        "مركز الفواتير",
        Capability.INVOICES_VIEW,
        "invoices",
        "فواتير الفوز وما سُدّد منها وما تأخّر.",
        "file",
    ),
    Page(
        "console:invoice-lookup",
        "حالة فاتورة",
        Capability.INVOICE_LOOKUP,
        "invoices",
        "حالةُ فاتورة مركبةٍ بعينها للتأمين والجهات الخارجية — بلا مشترٍ ولا مبلغ.",
        "magnifier-file",
    ),
    Page(
        "console:invoices-export",
        "تصدير الفواتير",
        Capability.INVOICES_VIEW,
        "invoices",
        "مدىً من التواريخ، وعددُ الصفوف يُرى قبل أن يبدأ التنزيل.",
        "download",
    ),
    # ---- التقارير والتحليلات — بترتيب v1 وأسمائه ---------------------------
    Page(
        "console:active-auction",
        "احصائيات المزاد النشط",
        Capability.AUCTIONS_VIEW,
        "reports",
        "صورةُ المزاد الجاري، وقيمتُه **لو أُغلق الآن** — رقمٌ يُقال شرطُه.",
        "gauge",
    ),
    Page(
        "console:analytics",
        "لوحة التقارير",
        Capability.AUCTIONS_VIEW,
        "reports",
        "مركزُ الأرقام — وكلُّ رقمٍ يُقرأ من مصدر شاشته لا من استعلامٍ ثانٍ.",
        "clipboard",
    ),
    Page(
        "console:profit-report",
        "تقرير الأرباح",
        Capability.MONEY_VIEW,
        "reports",
        "ما أنتجه كل مزاد وما فُوتِر منه وما وصل — ثلاثةُ أرقامٍ لا ضربٌ في نسبة.",
        "coins",
    ),
    Page(
        "console:analytics-bids",
        "تحليل المزايدات",
        Capability.AUCTIONS_VIEW,
        "reports",
        "حالات المزايدات قسمةً يساوي مجموعُها الإجمالي، وأكثر المزايدين نشاطاً.",
        "trend",
    ),
    # T832. جارتاها تجيبان سؤالين آخرين: «تحليل المزايدات» فوقها تعطي **عشرةً**
    # ثابتين بلا ترشيحٍ ولا صفحات، و«تقرير مزايدات مستخدم» في قسم الأعضاء
    # تُسأل عن **شخصٍ تعرف اسمه أو جوّاله** ولا تفتح قبله. وهذه تجيب «مَن»:
    # ألفٌ وثمانمئة مزايدٍ مرتّبين، مع ما فاز به كلٌّ منهم — وهو ما يُسأل قبل
    # منح حدّ ائتمان أو عند نزاع.
    Page(
        "console:bids-report",
        "تقرير المزايدات",
        Capability.AUCTIONS_VIEW,
        "reports",
        "كلُّ من زايد مرتّبين: كم مزايدة، على كم مركبة، وكم رسا له فعلاً.",
        "rank-bars",
    ),
    # ---- الإشعارات والدعم — بترتيب v1 وأسمائه ------------------------------
    Page(
        "console:broadcast",
        "إرسال إشعار",
        Capability.NOTIFICATIONS_SEND,
        "support",
        "الجمهورُ يُرشَّح ويُعَدّ والكلفةُ تُعرَض قبل الزرّ — والإدراجُ مؤجَّل.",
        "send",
    ),
    Page(
        "console:notifications",
        "سجل الإشعارات",
        Capability.NOTIFICATIONS_VIEW,
        "support",
        "ما أُرسل إلى من، وفي أي حالةٍ توقّف.",
        "bell",
    ),
    # T921. `content.manage` لا `notifications.view`: تلك قراءةُ ما أُرسل
    # ويحملها الدعم، وهذه **كتابةٌ تخرج إلى كلّ زائر**.
    Page(
        "console:news",
        "شريط الأخبار",
        Capability.CONTENT_MANAGE,
        "support",
        "الجملةُ التي تمرّ لكلّ زائر — بنافذتها الزمنيّة، وقيدُ كلِّ تغييرٍ باسم كاتبه.",
        "megaphone",
    ),
    # ---- النظام والصلاحيات — بترتيب v1 وأسمائه -----------------------------
    Page(
        "console:owners-console",
        "منصة الملاك",
        Capability.AUCTIONS_VIEW,
        "system",
        "أرقامُ المنصّة السبعة، وكلٌّ منها من مصدر شاشته — ولا تعديلَ مزايدة.",
        "crown",
    ),
    Page(
        "console:auction-bids-index",
        "مزايدات حسب المزاد",
        Capability.AUCTIONS_VIEW,
        "system",
        "اختر مزاداً لتفتح مزايداته بحالة كلٍّ منها.",
        # كان `list-check` وهو نفسُه على «مزايدات السيارات». والمطرقةُ فوق
        # الصفّين تقول «مزايدات»، والسطورُ وحدها تبقى لتلك.
        "gavel-rows",
    ),
    Page(
        "console:password-change",
        "تغيير كلمة المرور",
        Capability.CONSOLE_ACCESS,
        "system",
        "بمُصادقات جانغو — أقوى من شرطَي v1، فلا يُنقلان.",
        "key",
    ),
    Page(
        "console:audit",
        "سجل التدقيق",
        Capability.AUDIT_VIEW,
        "system",
        "من غيّر ماذا ومتى، بالقيمة قبل وبعد.",
        "search",
    ),
    Page(
        "console:odoo-inbox",
        "صندوق وارد أودو",
        Capability.ODOO_INBOX,
        "system",
        "ما وصل من أودو، وما فشل منه ولماذا، وإعادة تشغيله.",
        "inbox",
    ),
    Page(
        "console:settings",
        "الإعدادات",
        Capability.CONSOLE_ACCESS,
        "system",
        "حسابُك وما تملكه من قدرات، والمظهر — وما لكلٍّ منها من شاشة.",
        "sliders",
    ),
    # ---- شريك التسويق — بترتيب v1 وأسمائه ----------------------------------
    Page(
        "console:partner-console",
        "لوحة الشريك",
        Capability.PARTNERS_DECIDE,
        "partner",
        "أرقامُ شريكٍ واحد — وكلُّها من الفاتورة لا من جدولٍ يُرفع بملفّ.",
        "briefcase",
    ),
    Page(
        "console:partner-soon",
        "المزادات القادمة",
        Capability.PARTNERS_DECIDE,
        "partner",
        "مزاداتُه المجدولة، ومعها عدد سياراته هو لا عدد سيارات المزاد.",
        "calendar",
    ),
    Page(
        "console:partner-active",
        "المزاد الشغال",
        Capability.PARTNERS_DECIDE,
        "partner",
        "المزاد الجاري الآن وما لشريكك فيه.",
        "play",
    ),
    Page(
        "console:partner-ended",
        "المزادات المنتهية",
        Capability.PARTNERS_DECIDE,
        "partner",
        "ما انتهى من مزاداته، وما بيع في كلٍّ منها.",
        "flag",
    ),
    Page(
        "console:partner-auctions",
        "كل المزادات",
        Capability.PARTNERS_DECIDE,
        "partner",
        "مزاداته كلُّها بحالاتها، بلا ترشيحٍ على الحالة.",
        "layers",
    ),
    Page(
        "console:partner-vehicles",
        "كل السيارات",
        Capability.PARTNERS_DECIDE,
        "partner",
        "سياراته ونتيجةُ كلٍّ منها — وسعرُ وقوفها الحقيقي لا صفراً.",
        "car-list",
    ),
    Page(
        "console:partner-rule",
        "حكم الشريك على سيارته",
        Capability.PARTNERS_DECIDE,
        # **بلا قسم — فلا صفَّ لها في الشريط.** مسارُها يأخذ `pk` (سيارةٌ
        # بعينها)، و`{% url %}` في القالب مكتوبةٌ `as page_href` فتبتلع
        # `NoReverseMatch` وتُخرج `href=""` — أي رابطاً في الشريط **يعيد
        # تحميل الصفحة الحالية**. وهو بالضبط ما يمنعه T831: المحجوز يقول إنه
        # محجوز، ولا مدخلَ ميّتٌ بينهما. وليست في قائمة v1 أصلاً: هي فعلٌ في
        # صفّ سيّارةٍ داخل «كل السيارات» (`stampDecision`) لا مدخلَ منيو.
        # وأختاها اللتان تأخذان `pk` (`reminder-send` و`vehicle-bid-list`)
        # بلا قسمٍ كذلك — فهذه كانت الشاذّة.
        "",
        "قبولُ الشريك أو رفضُه — وهو ما يأذن للمنصّة أن تقرّر بعده.",
        "stamp",
        parent="console:partner-vehicles",
    ),
    Page(
        "console:partner-decisions",
        "اتخاذ القرار",
        Capability.PARTNERS_DECIDE,
        "partner",
        "مركبات انتهت مزايدتها دون سعر الوقوف — يقبل المالك أو يرفض.",
        "scale",
    ),
    Page(
        "console:partner-unpaid",
        "غير المسددة",
        Capability.PARTNERS_DECIDE,
        "partner",
        "ما رسا ولم يصل مالُه — من حالة الفاتورة لا من ملفٍّ مرفوع.",
        "hourglass",
        parent="console:partner-console",
    ),
    Page(
        "console:partner-paid",
        "المسددة",
        Capability.PARTNERS_DECIDE,
        "partner",
        "ما وصل مالُه فعلاً، بفاتورته وتاريخها.",
        "check",
    ),
    Page(
        "console:partner-payments",
        "سجل الدفعات",
        Capability.PARTNERS_DECIDE,
        "partner",
        "الدفعات المسجَّلة في الدفتر — رقمٌ واحد للمحاسبة وللشريك.",
        "receipt",
    ),
    Page(
        "console:partner-payments-approve",
        "اعتماد مدفوعات الشريك",
        Capability.MONEY_ACT,
        "partner",
        "ملفُّ الدفعات يُقيَّد في الدفتر — وبصمتُه تمنع رفعه مرّتين.",
        "upload",
        parent="console:partner-payments",
    ),
)


#: ما بقي من قائمة v1 ولم يُبنَ بعد — بترتيبها وأسمائها كما لصقها المالك. T831.
#:
#: ثمانيةٌ وأربعون مدخلاً. ومع السبعة عشر المبنيّة تكتمل القائمة التي يعرفها
#: الموظّف: واحدٌ وستّون مدخلَ v1، وأربعةٌ من عند v2 لا مقابل لها هناك (لوحة
#: التحليلات · استيراد المركبات · سجل التدقيق · صندوق وارد أودو).
#:
#: **الترتيب داخل هذه القائمة هو ترتيب v1**، غير أن `sidebar_for` يضع المبنيَّ
#: أولاً في كل قسم ثم هذه بعده — لا مختلطةً بينها. وذلك خروجٌ عن «نفس القائمة»
#: بقرار: القسم الواحد فيه اليوم أربعة مبنيّةٍ وثمانيةٌ محجوزة، ومخالطتُها
#: تجعل الوصول إلى شاشةٍ **تعمل** بحثاً في اثنتي عشرة سطراً بدل أربعة. والثمن
#: أن الذاكرة العضلية لموضع السطر تسقط — وهي تسقط في الحالتين ما دام نصفُ
#: القائمة لا يُفتح، وتعود كاملةً حين يُبنى الباقي ويفرغ هذا السجلّ.
#:
#: ويُحذف الصفّ من هنا **في نفس الالتزام** الذي يضيف صفَّه في `PAGES`. ولا
#: يُترك: مدخلٌ يقول «قريباً» وصفحتُه تعمل هو أسوأ من الاثنين معاً، ويمسكه
#: `test_navigation.py::test_nothing_is_promised_and_built_at_once`.
PLANNED: tuple[Planned, ...] = (
    # ---- إدارة الأعضاء ---------------------------------------------------
    # v1 يخزّن الصلاحية في جدولَي `cards` و`role_card_permissions` بمفتاحٍ
    # نصّيٍّ حرّ — سبعةَ عشرَ صفّاً مكرَّراً وأربعةٌ بلا وجهة (الشاشة ٣٧-ب).
    # ولذلك تُبنى صلاحياتٍ مسمّاةً لا كروتاً، ومنحُ الموظّف بابُه `StaffGrant`.
    # ---- إدارة المزادات --------------------------------------------------
    # ---- قرارات المزايدات ------------------------------------------------
    # ---- المالية والمدفوعات ----------------------------------------------
    # «إدارة الطلبات» (`/requests`) حُذفت هنا في ١٤ سبتمبر ٢٠٢٦ — **وهي مبنيّةٌ
    # باسمٍ آخر**: «طلبات الشحن البنكي» في قسم المحفظة. والقياسُ من دَمب
    # الإنتاج هو ما حسم أنهما واحد: شاشةُ v1 تَعِد بخمسة أقسام (استرداد ·
    # استلام · نقل ملكية · توصيل · تنازل)، وجدولُها `transfer_requests` فيه
    # ٢٣٢ صفّاً **كلُّها** `request_type='wallet_topup'` و`payment_method='bank'`،
    # وصفرُ طلبِ نقلِ ملكيّة. فالعاملُ منها قسمٌ واحد، وهو هذا.
    #
    # والاسمُ لم يُنقل معها: «إدارة الطلبات» يَعِد الموظّفَ بالأقسام الخمسة
    # فيفتحها ويجد طابوراً بنكيّاً، و«طلبات الشحن البنكي» يقول ما فيه. وما
    # بقي من الأقسام الأربعة له شاشتُه المسمّاة حيث يُقصَد — الاستردادُ في
    # «طلبات الاسترداد»، ونقلُ الملكية في «الخروج ونقل الملكية».
    # «الاشتراكات» (`/finance/subscriptions`) حُذفت في ١٤ سبتمبر ٢٠٢٦ — **لا
    # لأنها ناقصةٌ عندنا، بل لأن مصدرَها ليس عندنا أصلاً**. فُتّش دَمبُ
    # الإنتاج كلُّه (`hara_clone_v1_data_20260905_1444`): **مئةٌ وتسعةٌ
    # وثمانون جدولاً، وصفرٌ منها فيه `subscription` في اسمه**. أي أن شاشة v1
    # نفسَها لا تقرأ من قاعدة v1.
    #
    # والاشتراكاتُ تعيش في أودو: `apps/odoo/envelope.py` يرسل
    # `create/payment/subscription`، و`apps/odoo/reconciliation.py` يقرأ
    # `sale.subscription` بـ`call_kw` ليحسب الرصيد. فشاشةٌ هنا تعني نسخةً
    # ثانيةً من دفترٍ ليس دفترَنا — وهو بالضبط ما تمنعه أطروحةُ v2: الرقمُ
    # يُقرأ من مصدره لا من عمودٍ محفوظٍ عنه.
    # ---- المحفظة ---------------------------------------------------------
    # ---- الفواتير --------------------------------------------------------
    # «قائمة الفواتير» (`/bills/list`) حُذفت في ١٤ سبتمبر ٢٠٢٦ — **مبنيّةٌ
    # وأوسع**. وصفُ v1 لها بالحرف «الفواتير المحلية المرتبطة بالعملاء»، أي
    # جدولُ `invoices` — و**فيه صفرُ صفٍّ في دَمب الإنتاج**. والفواتيرُ
    # الحقيقيّةُ في `invoices_odoo` (١٢٬٤٣٤ صفّاً)، وهي جدولٌ آخرُ لا تعرضه
    # تلك الشاشة.
    #
    # وقُيست التغطيةُ لا خُمّنت (`haraj2_t307`، ١٤ سبتمبر ٢٠٢٦): «مركز
    # الفواتير» (`console:invoices`) يعرض **١٢٬٣٣١ فاتورة** — ١٢٬٣٢٤ منها
    # مصدرُها `odoo_sync` — بحالةٍ مشتقّةٍ من دفعاتها، وبمرشّح حالةٍ وبحثٍ
    # بالرقم والاسم والجوّال وتصدير. ومعه «تفاصيل الفاتورة» و«حالة فاتورة»
    # (`invoices.lookup`، للجهات الخارجية) و«تصدير الفواتير» بمدىً من
    # التواريخ. فالمدخلُ المحجوز كان يَعِد بصفرِ صفٍّ بجوار شاشةٍ تعرض اثني
    # عشر ألفاً.
    # ---- التقارير والتحليلات ---------------------------------------------
    # «تقرير المزايدات» بُنيت — انظر صفَّها في `PAGES` فوق (T832).
    # ---- الإشعارات والدعم ------------------------------------------------
    # **باقٍ عمداً — والقياسُ هو الذي أبقاه.** كان مرشَّحاً للحذف مع الخمسة في
    # ١٤ سبتمبر ٢٠٢٦، والجداولُ الخمسة التي تحمل اسمَ «support» في دَمب
    # الإنتاج تبدو مهجورة: `support_tickets` **٠** · `haraj_support_tickets`
    # **٠** · `support_chat_sessions` **٠** · `support_replies` **٤** ·
    # `support_messages` **٢٢٠** (استمارةُ «اتصل بنا»، آخرُ صفٍّ فيها
    # ٢٠٢٦-٠٢-١٤).
    #
    # **والشاتُّ العاملُ ليس فيها.** هو عائلةُ `haraj_chat_*`:
    # `haraj_chat_conversations` **٩٣٬٢٩٥ محادثة** و`haraj_chat_messages`
    # **٩٣٬٢٦١ رسالة** بين ٢٠٢٦-٠٥-١٤ و**٢٠٢٦-٠٩-٠٥ ١٤:٤٤** — وهي **لحظةُ
    # أخذ النسخة نفسُها** (`…_20260905_1444`). أي أن الرسائل كانت تصل حتى
    # الثانية التي أُخذ فيها الدَمب، ومعها موظّفان في `haraj_chat_staff`.
    #
    # فهذا نظامٌ **حيٌّ يعمل عليه بشر**، لا مدخلٌ يَعِد بشاشةٍ فارغة. وترحيلُه
    # قرارُ مالكٍ — شاتٌّ حيٌّ له تاريخُه وجلساتُه وموظّفوه، ونقلُه أو تركُه
    # على `support_panel/` قرارُ تشغيلٍ لا قرارُ شاشة. ويبقى المدخلُ محجوزاً
    # حتى يُتّخذ.
    Planned("الدعم الفني", "support", "/support_panel/admin_chat.php"),
    # ---- النظام والصلاحيات -----------------------------------------------
    # «إدارة الكروت» (`/cards`) و«صلاحيات الأدوار» (`/cards/permissions`)
    # حُذفتا في ١٤ سبتمبر ٢٠٢٦ — **النظامُ نفسُه مبنيٌّ بشكلٍ آخر، ويعمل**.
    #
    # وهما في v1 نصفا آليّةٍ واحدة: `cards` (٨٠ صفّاً في دَمب الإنتاج) قائمةُ
    # «كروت» كلُّ كرتٍ منها شاشةٌ أو زرّ، و`card_permissions` (٤٥ صفّاً) و
    # `role_card_permissions` (٨٤٩ صفّاً) تربطانها بالأدوار — و`roles` أربعةَ
    # عشرَ صفّاً، أربعةٌ منها تكرارُ أربعةٍ بأسماءٍ مختلفة. أي أن الصلاحيةَ
    # هناك **مفتاحٌ نصّيٌّ حرّ** يُكتب في جدول ويُقرأ في شاشة، ولا شيء يمنع
    # كرتاً بلا وجهةٍ ولا وجهةً بلا كرت.
    #
    # وعندنا القدرةُ **تعدادٌ في الشيفرة** (`Capability`) يقرؤه الشريطُ
    # والحارسُ معاً من `PAGES` — فلا مدخلَ بلا حارسٍ ولا حارسَ بلا مدخل
    # (رأسُ هذا الملفّ). والدورُ `ConsoleRole` حزمةَ قدراتٍ يُنشئها المالك،
    # والاستثناءُ فوق الدور `StaffGrant`. وشاشتاهما «إدارة المشرفين» و«صلاحيات
    # موظف» تعملان (T838). فبناءُ شاشةِ كروتٍ فوق ذلك يعني نظامَي صلاحيّاتٍ
    # في لوحةٍ واحدة — وهو بعينه عطلُ v1 الذي بُني هذا الملفُّ لأجل ألّا
    # يتكرّر.
    #
    # «إعدادات الحساب» (`/account-page`) حُذفت في ١٤ سبتمبر ٢٠٢٦ — **ليست من
    # اللوحة أصلاً**. اسمُها يقول «إعدادات حساب الموظّف»، وجدولُها
    # `account_page_settings` (١٢ صفّاً في دَمب الإنتاج) **محتوى واجهة
    # العميل**: نصوصُ الصفحات والشروطُ والأحكام. أي أنها CMS لواجهةٍ لا شاشةَ
    # إدارة، ومكانُها الفيز ٠١١ (واجهة العميل) لا هنا. وما يخصّ حسابَ الموظّف
    # مبنيٌّ: «الإعدادات» و«تغيير كلمة المرور» في هذا القسم نفسِه.
    # ---- شريك التسويق ----------------------------------------------------
)

#: Pages that take an id and therefore cannot appear in a sidebar — a link to
#: "the vehicle" means nothing without saying which. They are still rows here
#: because the guard reads this registry and nothing else, and a detail page
#: with no row would be a page with no guard.
DETAIL_PAGES: tuple[Page, ...] = (
    # «التحكم في صفحات المستخدمين» **دُمج في «إدارة المشرفين»** (T847): في v1
    # هما شاشتان تعرضان القائمة نفسها بعمودٍ مختلف، فيفتح الموظّف إحداهما ثم
    # يكتشف أن ما يريده في الأخرى بالاسم نفسه تقريباً. فصارت تُفتح من صفِّ
    # المشرف وخرجت من الشريط — مدخلان إلى القائمة الواحدة أحدُهما زائد.
    Page(
        "console:page-control",
        "التحكم في صفحات مشرف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    # تُفتح بزرٍّ من «إدارة المشرفين» لا من الشريط: إنشاءُ حسابٍ فعلٌ
    # على تلك القائمة لا وجهةٌ يُذهب إليها ابتداءً.
    Page(
        "console:admin-new",
        "إضافة مشرف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:admin-edit",
        "تعديل مشرف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:admin-password-reset",
        "إعادة تعيين كلمة مرور مشرف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:admin-delete",
        "حذف مشرف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:role-edit",
        "تعديل دور",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:role-delete",
        "حذف دور",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:auction-detail",
        "تفاصيل المزاد",
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-bids",
        "مزايدات المزاد",
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:vehicle-detail",
        "تفاصيل المركبة",
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:vehicles",
    ),
    Page(
        "console:vehicle-state",
        "تغيير حالة المركبة",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:vehicles",
    ),
    Page(
        "console:vehicle-relist",
        "إعادة عرض مركبة",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:vehicles",
    ),
    Page(
        "console:auction-new",
        "مزاد جديد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-edit",
        "تعديل مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-state",
        "نقلة مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    # العمليّات السريعة — T846. كلُّها `AUCTIONS_MANAGE`: من يرى القائمة
    # (`AUCTIONS_VIEW`) لا يُنهي مزاداً بضغطة.
    Page(
        "console:auction-showcase",
        "حالة مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-reschedule",
        "جدولة مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-fees",
        "رسوم مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    # حذفٌ بقدرةٍ خاصّة — أضيق من `AUCTIONS_MANAGE`: من يدير مزاداً يومياً
    # لا يُعطى زرّاً يمحوه.
    Page(
        "console:auction-delete",
        "حذف مزاد",
        Capability.AUCTIONS_DELETE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-vehicles-bulk",
        "عمليات مجمّعة على المركبات",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:auction-end-now",
        "إنهاء مزاد",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:auctions",
    ),
    Page(
        "console:vehicle-new",
        "مركبة جديدة",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:vehicles",
    ),
    Page(
        "console:vehicle-edit",
        "تعديل مركبة",
        Capability.AUCTIONS_MANAGE,
        "",
        parent="console:vehicles",
    ),
    # معرضُ الصور محروسٌ بـMANAGE لا VIEW: الشاشةُ نفسها ترفع وتحذف وتعيّن
    # غلافاً، وحارسٌ يفتحها لمن يملك العرض وحده يعني ثلاثةَ أفعالٍ يقف
    # دونها فحصٌ ثانٍ في الـview — وهو الموضع الثاني الذي يفترق (T801).
    Page(
        "console:vehicle-images",
        "صور المركبة",
        # **قراءةٌ لا إدارة** (٢٠٢٦-٠٩-١٤). كانت `AUCTIONS_MANAGE`، فموظّفُ
        # الساحة الذي يرى الكتالوج **لا يرى صورةَ سيّارةٍ إطلاقاً** — وv1 يفتح
        # المعرضَ لكلّ من يرى الشاشة. والصورةُ ما يُميّز السيّارةَ عن سطرِ نصّ.
        #
        # والرفعُ والحذفُ وتغييرُ صورةِ العرض تبقى `AUCTIONS_MANAGE`، محروسةً
        # في فرع `POST` من `vehicle_images.gallery` نفسِه — **وكان بلا فحصٍ
        # واحد**، متّكئاً على قدرة الصفحة وحدها.
        Capability.AUCTIONS_VIEW,
        "",
        parent="console:vehicles",
    ),
    # Downloads, not pages: a sidebar entry that starts a file download is a
    # link an operator clicks by accident.
    Page(
        "console:vehicles-export",
        "تصدير المركبات",
        Capability.AUCTIONS_IMPORT,
        "",
        parent="console:vehicles",
    ),
    Page(
        "console:vehicles-import-errors",
        "الصفوف المرفوضة",
        Capability.AUCTIONS_IMPORT,
        "",
        parent="console:vehicles-import",
    ),
    Page(
        "console:partner-offers",
        "العروض",
        Capability.PARTNERS_DECIDE,
        "",
        parent="console:partner-decisions",
    ),
    Page(
        "console:partner-award",
        "الترسية",
        Capability.PARTNERS_DECIDE,
        "",
        parent="console:partner-decisions",
    ),
    Page(
        "console:partner-reject",
        "رفض المالك",
        Capability.PARTNERS_DECIDE,
        "",
        parent="console:partner-decisions",
    ),
    Page(
        "console:customer-detail",
        "بيانات العميل",
        Capability.USERS_VIEW,
        "",
        parent="console:customers",
    ),
    Page(
        "console:customer-edit",
        "تعديل العميل",
        Capability.USERS_MANAGE,
        "",
        parent="console:customers",
    ),
    Page(
        "console:company-edit",
        "تعديل الشركة",
        Capability.USERS_MANAGE,
        "",
        parent="console:customers",
    ),
    Page(
        "console:customer-access",
        "وصول العميل",
        Capability.USERS_MANAGE,
        "",
        parent="console:customers",
    ),
    # قدرةٌ وحدها لا `users.manage`: انظر التعليق عند
    # `Capability.USERS_DELETE`.
    Page(
        "console:customer-delete",
        "حذف حساب",
        Capability.USERS_DELETE,
        "",
        parent="console:customers",
    ),
    # ليست `users.manage`: تعديلُ بيانات عميلٍ وتوسيعُ ما يستطيعه موظّف في
    # اللوحة كلّها ثقتان مختلفتان، وv1 جمعهما في علمٍ واحد.
    Page(
        "console:staff-grants",
        "صلاحيات موظف",
        Capability.STAFF_GRANT,
        "",
        parent="console:admins",
    ),
    Page(
        "console:invoice-detail",
        "تفاصيل الفاتورة",
        Capability.INVOICES_VIEW,
        "",
        parent="console:invoices",
    ),
    Page(
        "console:money-customer",
        "دفتر عميل",
        Capability.MONEY_VIEW,
        "",
        parent="console:money-ledger",
    ),
    # The three writes. `money-actions` carries `money.act`, and granting an
    # exception carries `money.exception` on top of it — the one action that
    # puts a bidder in an auction with nothing behind their bid is not the same
    # trust as confiscating a deposit that is already ours to take.
    # القراءة والإغلاق صلاحيتان: الدعم يقرأ الطابور ليجيب «أين استردادي؟»،
    # وإغلاقُ قضيةٍ قرارٌ يقول «لا استرداد» — وهو من ثقة `money.act`.
    Page(
        "console:refund-queue",
        "طابور عجز الاسترداد",
        Capability.MONEY_VIEW,
        "diagnostics",
        "أودو طلب سحب وديعةٍ مرهونة — ما لم يُنفَّذ وينتظر قراراً.",
        parent="console:refunds",
    ),
    Page(
        "console:refund-resolve",
        "إغلاق عجز استرداد",
        Capability.MONEY_ACT,
        "",
        parent="console:refund-queue",
    ),
    Page(
        "console:payment-attempts",
        "محاولات الدفع",
        Capability.MONEY_VIEW,
        "diagnostics",
        "ما حدث لمحاولة دفعٍ: لم تصل البوابة، أم رفضتها، أم نجحت ولم تُقيَّد.",
        parent="console:payments",
    ),
    Page(
        "console:money-actions",
        "أفعال مالية",
        Capability.MONEY_ACT,
        "",
        parent="console:money-ledger",
    ),
    Page(
        "console:money-confiscate",
        "مصادرة حجز",
        Capability.MONEY_ACT,
        "",
        parent="console:money-ledger",
    ),
    Page(
        "console:money-correct",
        "تصحيح حركة",
        Capability.MONEY_ACT,
        "",
        parent="console:money-ledger",
    ),
    Page(
        "console:money-exception",
        "منح استثناء مزايدة",
        Capability.MONEY_EXCEPTION,
        "",
        parent="console:money-ledger",
    ),
    Page(
        "console:odoo-message",
        "رسالة واردة",
        Capability.ODOO_INBOX,
        "",
        parent="console:odoo-inbox",
    ),
    Page(
        "console:odoo-replay",
        "إعادة تشغيل رسالة",
        Capability.ODOO_INBOX,
        "",
        parent="console:odoo-inbox",
    ),
    Page(
        "console:gateway-retry",
        "إعادة تشغيل طابور البوّابة",
        Capability.ODOO_INBOX,
        "",
        parent="console:odoo-inbox",
    ),
)


def pages_for(user) -> tuple[Page, ...]:
    """The pages ``user`` may open — and therefore exactly what they are shown.

    قدرات المستخدم تُقرأ **مرّةً واحدة**، لا مرّةً لكل صفٍّ
    ======================================================
    كانت `can(user, …)` تُنادى لكل صفحةٍ في السجلّ، وكلُّ نداءٍ منها استعلامٌ
    على `StaffGrant` — فرسمُ الشريط الجانبي وحده كان ثلاثة عشر استعلاماً،
    و**كلُّ شاشةٍ تُضاف كانت تجعل كل صفحةٍ في اللوحة أبطأ باستعلام**. كشفته
    T835: إضافة ثلاث شاشاتٍ رفعت صفحة «ليه ما يقدرش يزايد؟» من ١٩ استعلاماً
    إلى ٢٢، فأسقطت ميزانيةً مكتوبةً في اختبارٍ منذ T608.

    والإصلاح هنا لا في `can()`: حفظُ الجواب على كائن المستخدم كان سيجعل
    `can()` **ذات حالة** — واختبارٌ يمسك كائناً ويستدعي `can` بعد كتابة منحٍ
    عبر طلبٍ آخر كان سيقرأ القديم، ولا يُصلحه `refresh_from_db`. فبقيت `can()`
    نقيّة، وسُئلت `capabilities_of` مرّةً هنا حيث السؤال جماعيٌّ أصلاً.
    """
    allowed = capabilities_of(user)
    return tuple(page for page in PAGES if page.capability in allowed)


def sidebar_for(user) -> list[dict]:
    """الشريط: ما يُفتح أولاً في كل قسم، ثم ما لم يُبنَ بعد. T831.

    **والصلاحية تحكم المبنيّ وحده.** `PLANNED` تُعرض لكل من يفتح اللوحة —
    وليس ذلك تساهلاً، بل لأن ما لا يُفتح لا يُسرَّب: لا رابط ولا بيانات ولا
    استعلام، اسمٌ في قائمةٍ فقط. وربطُها بقدرةٍ كان سيعني اختراع قدرةٍ لكل
    شاشةٍ **لم تُكتب بعد**، وقدرةٌ لا تحرس شيئاً تُسقِط
    `every_capability_guards_something` — أي أن الحارس نفسه يرفض التخمين.

    وحين تُبنى الشاشة يُحذف صفُّها من `PLANNED` ويُضاف في `PAGES` **بقدرتها**،
    فتُخفى عمّن لا يملكها في اللحظة نفسها التي تصير فيها قابلةً للفتح.
    """
    allowed = pages_for(user)
    grouped = []

    for section in SECTIONS:
        built = [page for page in allowed if page.section == section.key]
        soon = [row for row in PLANNED if row.section == section.key]
        if built or soon:
            grouped.append({"label": section.label, "pages": built, "planned": soon})

    return grouped


def back_for(url_name: str) -> Page | None:
    """الشاشةُ التي يعود إليها زرُّ «رجوع» من ``url_name``، أو ``None`` للجذر. T864.

    ثلاث قواعد، وكلُّها من السجلّ لا من المتصفّح:

    * صفحةُ تفصيلٍ تعود إلى **أبيها المصرَّح**: مركبةٌ إلى المركبات، وقرارُ
      شريكٍ إلى قرارات الشركاء.
    * صفحةٌ في الشريط تعود إلى **الرئيسية**.
    * الرئيسيةُ نفسها لا زرَّ لها — الرجوعُ منها خروجٌ من اللوحة.

    ولماذا لا ``history.back()``
    ============================
    لأنه يعود إلى **الطلب** السابق لا إلى الشاشة السابقة. وبعد `POST` وإعادة
    توجيه يعود إلى الاستمارة المرسَلة، وفي تبويبٍ فُتح برابطٍ مباشر يخرج من
    الموقع كلّه إلى حيث كان القارئ قبله. والوجهةُ المصرَّحة تعرف أين تذهب في
    الحالتين، وتُقرأ قبل النقر لأنها تحمل **اسم** ما تعود إليه.
    """
    for page in (*PAGES, *DETAIL_PAGES):
        if page.url_name != url_name:
            continue
        if page.parent:
            return next(
                (row for row in (*PAGES, *DETAIL_PAGES) if row.url_name == page.parent),
                None,
            )
        if page.url_name == HOME:
            return None
        return next((row for row in PAGES if row.url_name == HOME), None)
    return None


def capability_for(url_name: str) -> str | None:
    """Which capability guards ``url_name``, or None when it is not a page here.

    Used by the guard decorator so a view names its page rather than repeating
    the capability — repeating it is how the two drift apart.
    """
    for page in (*PAGES, *DETAIL_PAGES):
        if page.url_name == url_name:
            return page.capability
    return None


__all__ = [
    "DETAIL_PAGES",
    "PAGES",
    "PLANNED",
    "SECTIONS",
    "Page",
    "Planned",
    "Section",
    "capability_for",
    "pages_for",
    "sidebar_for",
]
