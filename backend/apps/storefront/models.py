"""ما يقرؤه العميل ويحرّره الموظّف: شريطُ الأخبار وباقاتُ الاشتراك.

لماذا تطبيقٌ ثالثٌ لا `core` ولا `notifications`
================================================
`apps.core` أدواتٌ مشتركة — سجلُّ التدقيق والوقتُ والقفل — يستعملها كلُّ
تطبيق؛ ونموذجٌ له شاشةٌ وقواعدُ عملٍ فيه يجعل الطبقةَ التحتيّة تعرف نطاقاً
فوقها. و`apps.notifications` رسالةٌ **لشخصٍ بعينه** لها قناةٌ وحالةُ تسليم
(`Notification.channel` و`delivery_state`)، وشريطُ الأخبار جملةٌ تُعرَض
للجميع بلا مُرسَلٍ إليه ولا تسليمَ يُتتبَّع — وضعُها هناك كان سيعني صفّاً
بقناةٍ فارغةٍ وحالةٍ لا تنتقل.

والجامعُ بين النموذجين هنا ليس الموضوع بل **الاتّجاه**: كلاهما محتوىً
يكتبه الموظّف في اللوحة **ويخرج إلى واجهة العميل**. وهذا الاتّجاه هو ما
يفرض على الاثنين القاعدةَ نفسَها: لا حذفَ حقيقيّ، وقيدُ تدقيقٍ بالنصّ قبل
وبعد ومن كتبه.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone


class NewsTickerMessage(models.Model):
    """جملةٌ تمرّ في شريط أخبار واجهة العميل، بنافذةٍ زمنيّةٍ وعلمِ تفعيل.

    مقابلُها في v1 جدولُ `news_ticker`: `text_ar`/`text_en`/`start_at`/
    `end_at`/`is_active` وفهرسٌ على الثلاثة الأخيرة معاً. والأسماءُ هنا
    أوضح، والقيمُ هي هي.

    **النافذةُ الفارغة تعني «بلا حدّ» لا «غيرُ مجدولة» — مقروءةً من v1 لا
    مستنتجة.** قرّاءُ v1 الأربعة كلُّهم يكتبون الشرطَ نفسَه حرفياً
    (`index.php:3178`، `SystemApiController.php:46`،
    `NewsTickerController.php:25`):

        WHERE is_active = 1
          AND (start_at IS NULL OR start_at <= NOW())
          AND (end_at   IS NULL OR end_at   >= NOW())

    وشاشةُ v1 تقولها للموظّف بالحرف: «اتركهما فارغين ليظهر الخبر دائمًا
    طالما مُفعّل» (`src/Views/Admin/news/index.php:160`). والجدولُ وحده كان
    يكفي لاستنتاجها: `is_active` علمٌ **مستقلّ** عن التاريخين، فلو كان
    `start_at = NULL` يعني «لم تُجدوَل» لصار للإيقاف بابان.

    **والمتداخلتان تُعرَضان معاً** — مقروءةً كذلك: لا `LIMIT 1` في v1 بل
    `LIMIT 50`، والقارئ يلفّ النتائج كلَّها في `<span>` داخل مسارٍ واحدٍ
    يمرّ (`index.php:3203`). فالشريطُ يتوالى ولا يحجب أوّلُه آخرَه.
    """

    #: النصُّ كما يُعرَض. ٢٥٥ محرفاً كما في v1 — والشريطُ يمرّ أفقياً،
    #: فالجملةُ الطويلة تُقرأ بطيئةً لا تُقرأ أصلاً.
    #:
    #: **ومطلوبٌ هنا، وv1 لا يطلبه** — هناك يكفي أحدُ النصّين
    #: (`NewsTickerController.php:63`: ``if ($ar === '' && $en === '')``)،
    #: وثمنُ ذلك في قارئه: سلسلةُ `COALESCE` ترجع إلى العمود الآخر حين
    #: يفرغ الأوّل، فصفٌّ بالإنجليزيّة وحدها **يُعرَض إنجليزيّاً على زائرٍ
    #: عربيّ**. فالعربيّةُ أصلٌ هنا والإنجليزيّةُ زيادةٌ عليه، ولا يُعرَض
    #: لقارئٍ نصٌّ بلغةٍ لم يطلبها.
    text_ar = models.CharField("النص (عربي)", max_length=255)

    #: الإنجليزيّةُ اختياريّة. وv1 **يعرضها فعلاً** لزائرٍ اختار
    #: ``?lang=en`` (`index.php:3178`: العمودُ يُختار باللغة)، ولغاتُه
    #: أربع (`start.php:97`: ``['ar','en','ur','hi']``) غير أن الجدول
    #: عمودان فقط — فالأردية والهندية تقعان على العربية.
    #:
    #: وهي **تُخزَّن هنا ولا تُعرَض بعد**: لا واجهةَ عميلٍ إنجليزيّةً في v2
    #: اليوم، ولم أفتح واحدة. وأُبقي العمودُ لأن بياناتِ v1 فيه والهجرةُ
    #: (الفيز ٠٤) ستحملها، وإسقاطُه يعني فقدَها عند النقل.
    #: **ولا تُترجَم آليّاً**: جملةٌ تُعرَض على الناس تُكتب بيدٍ تعرف ما تقول.
    text_en = models.CharField("النص (إنجليزي)", max_length=255, blank=True)

    #: بدايةُ النافذة. فارغةٌ = «من الآن».
    starts_at = models.DateTimeField("يبدأ العرض", null=True, blank=True)

    #: نهايةُ النافذة. فارغةٌ = «بلا نهاية».
    ends_at = models.DateTimeField("ينتهي العرض", null=True, blank=True)

    #: مفتاحُ الإيقاف. **لا حذفَ حقيقيّ** — الرسالةُ خرجت إلى الناس، وقيدُ
    #: التدقيق يشير إلى صفٍّ بمعرّفه؛ فحذفُه يترك في السجلّ إشارةً إلى لا شيء.
    is_active = models.BooleanField("مفعّلة", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "رسالة شريط أخبار"
        verbose_name_plural = "رسائل شريط الأخبار"
        # الأحدثُ أوّلاً في اللوحة: الشاشةُ شاشةُ عملٍ لا إعداد — ستّةٌ من
        # تسعةِ صفوفٍ في v1 حُذفت، أي أن الكتابةَ والإيقاف يوميّان.
        ordering = ("-created_at", "-id")
        indexes = [
            # نفسُ فهرس v1 (`idx_active_time`) وبنفس ترتيب الأعمدة: السؤالُ
            # الذي يُسأل كثيراً هو «ما يُعرَض الآن».
            models.Index(
                fields=["is_active", "starts_at", "ends_at"],
                name="news_ticker_active_time",
            ),
        ]
        constraints = [
            # نافذةٌ تنتهي قبل أن تبدأ لا تعرض شيئاً أبداً، فهي خطأُ كتابةٍ
            # لا اختيار. والقيدُ في القاعدة لا في الاستمارة وحدها: الاستمارةُ
            # بابٌ واحد، و`shell` وهجرةُ الفيز ٠٤ بابان آخران.
            #
            # و`gte` لا `gt` — نفسُ حدّ v1 حرفياً (`NewsTickerController.php:68`
            # يرفض `$e < $s` وحدها): بدايةٌ تساوي نهايتَها نافذةُ لحظةٍ
            # واحدة، وطرفاها شاملان في `showing_now`، فهي تُعرَض تلك اللحظة.
            models.CheckConstraint(
                condition=(
                    Q(starts_at__isnull=True)
                    | Q(ends_at__isnull=True)
                    | Q(ends_at__gte=models.F("starts_at"))
                ),
                name="news_window_ends_after_it_starts",
            ),
            # نصٌّ فارغٌ أو فراغاتٌ يعني شريطاً يمرّ بلا كلام — وهو عطلٌ
            # صامت: لا خطأ، ومساحةٌ تتحرّك في صفحة العميل بلا معنى.
            models.CheckConstraint(
                condition=~Q(text_ar=""),
                name="news_text_ar_not_blank",
            ),
        ]

    def __str__(self) -> str:
        return self.text_ar[:60]

    @property
    def is_showing(self) -> bool:
        """أتُعرَض هذه الرسالةُ للعميل في هذه اللحظة؟

        نفسُ شروط :meth:`showing_now` بالضبط، محسوبةً على صفٍّ واحدٍ في
        بايثون — فالشاشةُ تقول لكلّ صفٍّ حالتَه بلا استعلامٍ ثانٍ لكلّ سطر.
        """
        now = timezone.now()
        return (
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or self.ends_at >= now)
        )

    @classmethod
    def showing_now(cls, at=None):
        """ما يُعرَض على واجهة العميل الآن — الاستعلامُ الوحيد لهذا السؤال.

        دالّةٌ واحدة لأن الشرطَ ثلاثيّ (`is_active` ونافذتان مفتوحتا
        الطرفين)، ونسخةٌ ثانيةٌ منه في نقطةِ API تعني تعريفين لـ«يُعرَض
        الآن» — وأولُ ما يتفارقان فيه هو الطرفُ الفارغ. وv1 نفسُه كتب
        الشرطَ في أربعة مواضع، ثم اختلف اثنان منها في الترتيب.

        **والطرفان شاملان كما في v1** (`start_at <= NOW()` و
        `end_at >= NOW()`) — لا اجتهادَ في ثانيةٍ واحدة: المنطقُ من v1.

        والترتيبُ ترتيبُه كذلك: `COALESCE(start_at, created_at) DESC, id
        DESC` — أي الأحدثُ أوّلاً، ورسالةٌ بلا بدايةٍ تُرتَّب بوقت كتابتها.
        """
        now = at or timezone.now()
        return (
            cls.objects.filter(
                Q(is_active=True)
                & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
                & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
            )
            .annotate(shown_from=Coalesce("starts_at", "created_at"))
            .order_by("-shown_from", "-id")
        )


class SubscriptionPeriod(models.TextChoices):
    """مدّةُ الاشتراك التي تشتريها الباقة — `packages.type` في v1، **مسمّاةً**.

    التعدادُ هناك `enum('1','2','3')` بلا أسماء، وذلك عطلٌ يُصلَح لا يُنقَل:
    شاشةُ v1 تعرضه رقماً خاماً (`Views/Admin/finance/packages/index.php:229`)
    وتقبله في **خانةٍ نصّيّةٍ حرّة** لا قائمةٍ (`form.php:274`)، فلا شيء
    يمنع كتابة `7`.

    **والمعنى مقروءٌ من v1 لا مخترَع**، ومن موضعين متّفقين:

    * قاموسُ الترجمة العامّ (`start.php:1441`) يحمل المفاتيح الثلاثة
      بأسمائها الأربعِ لغات: ``period_1`` «شهر واحد»، ``period_2``
      «3 أشهر»، ``period_3`` «6 أشهر» — ومثلُها في `menu/sub.php:71`.
    * والشيفرةُ التي كانت تقرؤها: `menu/sub.php` قبل الالتزام `9ca7364`
      («simplify insurance subscription flow»، ١٢ مايو ٢٠٢٦) يبني
      ``$periodKey = 'period_' . $type`` ويرسمه شارةً بجانب الباقة.

    **ولا شيء في v1 اليوم يقرأ هذا العمود.** سطرُ `$periodKey` باقٍ في
    `menu/sub.php:487` **ولا يُستعمل بعده**، والشارةُ صارت نصّاً ثابتاً؛ ولا
    `if` ولا `switch` ولا حسابَ تاريخِ انتهاءٍ من المدّة في الشجرة كلّها.
    فالمدّةُ اليومَ **لافتةٌ تُعرَض ولا تُحاسَب عليها**، وهذا يُكتب هنا كي
    لا تُبنى فوقه حسبةُ تجديدٍ لا وجود لها في النظام الذي نطابقه.
    """

    MONTH_1 = "1", "شهر واحد"
    MONTHS_3 = "2", "٣ أشهر"
    MONTHS_6 = "3", "٦ أشهر"


class Package(models.Model):
    """باقةُ اشتراك: مبلغُ تأمينٍ يُودَع، وحصّةُ مزاداتٍ يفتحها، ومدّة.

    مقابلُها `packages` في v1: صفٌّ واحدٌ حيٌّ و`AUTO_INCREMENT = 15`، أي
    أن أربعةَ عشرَ جُرِّبت ثم زالت. فالشاشةُ قليلةُ الاستعمال — **وذلك
    يُبسّطها ولا يُلغيها**: الصفُّ الواحدُ الباقي هو الذي يحكم من يزايد.

    ما تفعله الباقةُ فعلاً — مقروءاً من v1
    ======================================
    * **`price` ليس اشتراكاً شهريّاً، بل عتبةُ تأمينٍ مودَع.** بوّابةُ
      المزايدة (`bids_submit.php:173`) ترفض من كان
      ``total_insurance_paid < packages.price``، و`AccountApiController.php:776`
      يجعل التأمينَ المطلوبَ ``max(10000, price)``. ولا جدولَ `subscriptions`
      في v1 أصلاً — الاشتراكُ عمودُ `userss.id_package` وحده.
    * **`no_car` حصّةُ مزاداتٍ لا حصّةُ مركبات.** الاسمُ يقول «سيارات»
      والشيفرةُ تعدّ غيرَه: ``SELECT COUNT(DISTINCT auction_id) FROM bids
      WHERE user_id = ?`` (`bids_submit.php:223`)، ثم تمنع الإضافةَ عند
      بلوغ الحدّ (`:287`). فالاسمُ هنا `auction_quota` — واسمٌ يكذب أسوأُ
      من اسمٍ طويل.
    * **`active` في v1 لا يحرس شيئاً حيث يهمّ.** بوّابةُ المزايدة تصل
      الباقةَ بـ`JOIN packages p ON u.id_package = p.id` **بلا شرطٍ على
      `active`**، فإيقافُ باقةٍ لا يسحب حصّةَ أحد. وذلك ليس ما نبنيه: هنا
      الإيقافُ يعني «لا تُعرَض ولا تُسنَد من جديد»، والقارئُ الوحيد
      لـ«الباقات المعروضة» هو :meth:`offered`.

    ولماذا لا حذفَ حقيقيّ
    =====================
    v1 يحذف حذفاً حقيقيّاً (`PackageController.php:142`:
    ``DELETE FROM packages WHERE id = ?``) **بلا مفتاحٍ أجنبيّ ولا فحصٍ
    لـ`userss.id_package`**. وأثرُه مقيسٌ في شيفرته: الوصلةُ تفشل، فيصير
    `$subscription` كاذباً، فيقرأ **عميلٌ مشترِكٌ فعلاً** أن عليه إيداع
    تأمين. فالإيقافُ هنا (`is_active = False`) هو ما يفعله الجدولُ نفسُه
    بعمودِه، وهو ما يُبقي الأثر.
    """

    #: اسمُ الباقة كما يراه العميل. عمودٌ واحدٌ كما في المخطَّط المرصود
    #: (`name varchar(255)`)؛ وشاشةُ v1 تعرض حقلَي `name_ar`/`name_en`
    #: لعمودين **قد لا يوجدان** — فتكتب في `name` قيمةً لا تُرسِلها
    #: الاستمارة، أي اسماً فارغاً. لا يُنقل هذا.
    name = models.CharField("اسم الباقة", max_length=255)

    #: مبلغُ التأمين الذي تشترطه هذه الباقة. `Decimal` لا `float` —
    #: المادة ٣-٢، وهو مبلغٌ يُقارَن برصيدِ عميل.
    price = models.DecimalField("مبلغ التأمين", max_digits=10, decimal_places=2)

    description = models.TextField("الوصف", blank=True)

    #: `packages.type` في v1. القيمُ هي هي (`"1"`/`"2"`/`"3"`) كي تعبر
    #: هجرةُ الفيز ٠٤ بلا خريطة، والأسماءُ من قاموس v1.
    period = models.CharField(
        "المدّة",
        max_length=1,
        choices=SubscriptionPeriod.choices,
        default=SubscriptionPeriod.MONTH_1,
    )

    #: `packages.no_car` في v1 — **عددُ المزادات** التي يجوز للمشترك أن
    #: تكون له فيها مزايدة، لا عددُ السيارات.
    #:
    #: والصفرُ افتراضُ v1 (`ensure_feature_tables.php:157`) ومعناه هناك
    #: **منعُ كلّ مزايدةٍ جديدة** — لا «بلا حدّ». فهو يُعرَض هنا بهذا
    #: المعنى صراحةً في الشاشة، ولا يُقرأ «مفتوح».
    auction_quota = models.PositiveIntegerField("حصّة المزادات", default=0)

    is_active = models.BooleanField("مفعّلة", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "باقة"
        verbose_name_plural = "الباقات"
        # بالسعر صعوداً كما يرتّبها قارئُ v1 (`FinanceController.php:814`:
        # `ORDER BY price ASC, id DESC`) — الأرخصُ أوّلاً هو ما يقرؤه من
        # يختار، وأربعةَ عشرَ صفّاً زالت فلا قائمةَ طويلةً تُصفَّح.
        ordering = ("price", "-id")
        constraints = [
            # سعرٌ سالب يعني عتبةَ تأمينٍ يجتازها **كلُّ** رصيد، بما فيه
            # الصفر — أي باقةً تفتح المزايدة لمن لم يودع شيئاً. وv1 لا
            # يفحص شيئاً هنا إطلاقاً (`extractData` تمرّر `$_POST` كما هو).
            models.CheckConstraint(
                condition=Q(price__gte=Decimal("0")),
                name="package_price_not_negative",
            ),
            models.CheckConstraint(
                condition=~Q(name=""),
                name="package_name_not_blank",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def offered(cls):
        """الباقاتُ التي تُعرَض على العميل وتُسنَد إليه — المفعّلةُ وحدها.

        قارئٌ واحدٌ لهذا السؤال بدل شرطٍ يُكتب في كل موضع: في v1 كُتب
        `WHERE active = 1` في أربعة مواضعَ وسقط من أربعةٍ أخرى — منها
        بوّابةُ المزايدة نفسُها — فصار للعمود معنىً في نصف النظام ولا معنى
        في نصفه.
        """
        return cls.objects.filter(is_active=True)
