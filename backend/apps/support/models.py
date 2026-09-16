"""محادثاتُ الدعم: القسمُ، والمحادثةُ، والرسالة. T924.

مقابلُها في v1 عائلةُ `haraj_chat_*` — **نظامٌ حيٌّ يعمل عليه بشر**:
٩٣٬٢٩٥ محادثةً و٩٣٬٢٦١ رسالةً آخرُها في اللحظة التي أُخذ فيها دَمبُ الإنتاج
(`…_20260905_1444`). فهذه ليست شاشةً تُنقَل عن جدولٍ فارغ.

لماذا تطبيقٌ مستقلّ
==================
لأن المحادثةَ ليست إشعاراً. `apps.notifications` رسالةٌ **من النظام إلى
شخص** لها قناةٌ (`channel`) وحالةُ تسليم (`delivery_state`) وتنتهي عند
وصولها؛ والمحادثةُ **طرفان يتبادلان**، لها عمرٌ وقسمٌ ومُسنَدٌ إليه وإغلاق.
وضعُها هناك كان سيعني صفّاً بقناةٍ فارغةٍ وحالةِ تسليمٍ لا تنتقل — وهو نفسُ
ما رُفض لأجله وضعُ شريط الأخبار هناك (`apps.storefront`).

الجداولُ الثلاثةُ مقابلَ تسعةٍ في v1
====================================
في الدَمب تسعةُ جداولَ تحمل الاسم، وأكثرُها مهجور: `haraj_chat_agents` صفرُ
صفٍّ · `haraj_chat_notifications` اثنا عشر صفّاً لا يقرؤها قارئٌ في الشاشة ·
`haraj_chat_sessions` أربعةٌ وعشرون صفّاً هُجرت لصالح
`haraj_chat_conversations` · `haraj_chat_ratings` **صفٌّ واحد**. فالعاملُ
منها ثلاثة، وهي الثلاثةُ هنا.

**ولا جدولَ موظّفين رابعاً.** `haraj_chat_staff` في v1 جدولُ حساباتٍ مستقلٌّ
له `username` و`password_hash` خاصّان به — أي بابُ دخولٍ ثانٍ إلى الشركة
لا يعرفه `userss` ولا تحرسه أدوارُ اللوحة. وصفّاه الحيّان **كلاهما
`password_hash = NULL`**: حسابان في نظامٍ حيٍّ بلا كلمةِ مرورٍ أصلاً. فالموظّفُ
هنا هو `accounts.User` نفسُه الذي يدخل اللوحة، بقدرته وبدوره.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q


class Department(models.Model):
    """قسمٌ يستقبل المحادثات — ووجهتُه التي يختارها العميل.

    مقابلُه `haraj_departments` (أربعةُ صفوفٍ حيّة: ``ai`` · ``support`` ·
    ``finance`` · ``orders``، والمعرّفُ ٤ محذوف). والأعمدةُ هي هي عدا اثنين:

    * **`is_open` لا `is_online`** — «متّصل» يقولها حضورُ موظّف، و`is_online`
      في v1 علمٌ يكتبه الأدمن بزرٍّ ولا علاقةَ له بأحدٍ حاضر. فالاسمُ كان
      يَعِد بما لا يقيس، والمعنى المقصود «القسمُ يستقبل طلباتٍ جديدة».
    * **`name_en` يُخزَّن ولا يُعرَض**: واجهةُ العميل عربيّةٌ اليوم، والعمودُ
      يُملأ حين تُبنى الإنجليزيّة — ونفسُ قرارِ `text_en` في
      :mod:`apps.storefront`، وللسبب نفسِه: بياناتُ v1 فيه.

    **وقسمُ ``ai`` لا يُنقَل.** شاشةُ v1 ترشّحه من القائمة بسطرٍ صريح
    (`admin_chat.php:73`) — أي أن الجدولَ يحمل صفّاً تُخفيه الشاشةُ التي
    تقرؤه. وما لا يُعرَض لا يُنقَل.
    """

    code = models.CharField("المعرّف", max_length=50, unique=True)
    name_ar = models.CharField("الاسم", max_length=100)
    name_en = models.CharField("الاسم (إنجليزي)", max_length=100, blank=True)

    #: هل يستقبل القسمُ محادثاتٍ جديدة. **والمحادثاتُ القائمةُ تبقى** — إغلاقُ
    #: البابِ لا يطرد من في الغرفة، ومحادثةٌ يردّ عليها موظّفٌ لا تنقطع لأن
    #: زميلَه أوقف الاستقبال.
    is_open = models.BooleanField("يستقبل محادثات", default=True)

    #: ترتيبُ العرض. v1 يرتّب بالمعرّف، فحذفُ قسمٍ وإعادةُ إنشائه تنقله إلى
    #: آخر القائمة بلا أن يطلب ذلك أحد.
    position = models.PositiveSmallIntegerField("الترتيب", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "قسم دعم"
        verbose_name_plural = "أقسام الدعم"
        ordering = ("position", "id")

    def __str__(self) -> str:
        return self.name_ar


class Conversation(models.Model):
    """محادثةٌ واحدةٌ بين عميلٍ وقسم.

    مقابلُها `haraj_chat_conversations`، وأعمدتُها هي هي إلا أربعةً:

    * **`customer` مفتاحٌ أجنبيّ لا عمودُ رقمٍ حرّ** — في v1 `user_id` عمودُ
      `int` بلا قيدٍ إلى `userss`، ومعه `user_name` نصّاً منسوخاً. وثمنُ ذلك
      مقيسٌ في الدَمب: اسمٌ منسوخٌ يبقى كما كان يومَ الكتابة، فمن غيّر اسمَه
      صار له اسمان في اللوحة. والاسمُ هنا يُقرأ من الحساب، و`guest_name`
      لمن لا حسابَ له.
    * **`assigned_to` إلى `accounts.User`** لا إلى جدولِ موظّفين ثانٍ.
    * **`last_message_at` عمودٌ مخزَّن** — انظر أدناه.
    * **`closed_by` و`closed_reason`**: v1 يكتب `closed_at` ولا يكتب من
      أغلق ولا لماذا، فالسؤالُ الذي يُسأل بعد شكوى — «من أغلق محادثتي؟» —
      لا جوابَ له في الجدول.
    """

    #: القسمُ حمايةً لا تسلسلاً: حذفُ قسمٍ له آلافُ المحادثات يفقدها.
    department = models.ForeignKey(
        Department,
        verbose_name="القسم",
        on_delete=models.PROTECT,
        related_name="conversations",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="العميل",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="support_conversations",
    )

    #: اسمُ من لا حسابَ له — وهو الأكثرُ في v1 لا الاستثناء.
    guest_name = models.CharField("اسم الزائر", max_length=190, blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="مُسنَدة إلى",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
    )

    #: لغةُ المحادثة كما بدأها العميل.
    language = models.CharField("اللغة", max_length=2, default="ar")

    opened_at = models.DateTimeField("بدأت", auto_now_add=True)
    closed_at = models.DateTimeField("أُغلقت", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="أغلقها",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_conversations",
    )
    closed_reason = models.CharField("سببُ الإغلاق", max_length=255, blank=True)

    #: وقتُ آخر رسالة — **عمودٌ مخزَّن، وهو الاستثناء الوحيد هنا لقاعدة
    #: «الرقمُ يُقرأ من مصدره»**، وحجّتُه مقيسة.
    #:
    #: v1 يشتقّه في كلّ طلب: استعلامُ القائمة فيه وصلٌ على استعلامٍ فرعيٍّ
    #: فيه `GROUP BY conversation_id` على **الجدول كلِّه** (٩٣ ألف رسالة)،
    #: ثم وصلٌ ثانٍ على استعلامٍ فرعيٍّ ثانٍ يعدّ رسائل العميل، ثم ترتيبٌ على
    #: مخرجهما. وصفحةُ اللوحة تُعيده **كلَّ أربع ثوانٍ** من `admin_poll.php`
    #: لكلّ تبويبٍ مفتوح.
    #:
    #: وكاتبُه **واحد**: :func:`apps.support.services.post_message` وحدَه،
    #: في الموضع الذي يُدرج الرسالة. فلا يُكتب في شاشةٍ ولا في هجرةٍ بيدها.
    last_message_at = models.DateTimeField("آخر رسالة", null=True, blank=True)

    class Meta:
        verbose_name = "محادثة دعم"
        verbose_name_plural = "محادثات الدعم"
        # الأحدثُ كلاماً أوّلاً — وهو ترتيبُ شاشةِ v1 نفسُه، غير أنه هنا
        # يقرأ عموداً مفهرساً بدل ترتيبٍ على مخرج استعلامين فرعيّين.
        ordering = ("-last_message_at", "-id")
        indexes = [
            models.Index(
                fields=["department", "-last_message_at"],
                name="support_conv_dept_recent",
            ),
            # سؤالُ «ما المفتوحُ الآن؟» يُسأل في كل تحميلٍ للشاشة.
            models.Index(
                fields=["closed_at"],
                condition=Q(closed_at__isnull=True),
                name="support_conv_open",
            ),
        ]
        constraints = [
            # محادثةٌ بلا عميلٍ ولا اسمِ زائرٍ صفٌّ لا يُعرف صاحبُه —
            # و`user_name` في v1 عمودٌ مطلوبٌ بلا قيدٍ على الفراغ، فالصفُّ
            # الفارغ يمرّ ويُعرَض سطراً بلا اسم.
            models.CheckConstraint(
                condition=Q(customer__isnull=False) | ~Q(guest_name=""),
                name="support_conv_has_a_name",
            ),
            # من أغلق ومتى يقعان معاً: إغلاقٌ باسمٍ بلا وقتٍ يقول إن أحداً
            # أغلق محادثةً ما زالت مفتوحة.
            models.CheckConstraint(
                condition=Q(closed_by__isnull=True) | Q(closed_at__isnull=False),
                name="support_conv_closed_by_needs_a_time",
            ),
        ]

    def __str__(self) -> str:
        return f"محادثة #{self.pk} — {self.display_name}"

    @property
    def display_name(self) -> str:
        """اسمُ الطرف الآخر — من الحساب إن وُجد، وإلا اسمُ الزائر."""
        if self.customer_id is not None:
            return self.customer.full_name or self.customer.phone
        return self.guest_name

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


class SenderKind(models.TextChoices):
    """من كتب الرسالة. **ثلاثُ قيمٍ في عمودٍ واحد، لا ستٌّ في عمودين.**

    v1 يحمل عمودين لنفس السؤال بمفرداتٍ مختلفة:
    ``sender`` من ``user|bot|agent`` و``sender_type`` من ``user|bot|staff``.
    و`conversation_action.php` يكتب في الثاني القيمةَ ``admin`` — **وهي
    ليست في التعداد أصلاً**: في وضع MySQL المتساهل تُخزَّن سلسلةً فارغةً بلا
    خطأ، فردُّ الموظّف يصير صفّاً لا نوعَ له.
    """

    CUSTOMER = "customer", "العميل"
    STAFF = "staff", "الموظّف"
    SYSTEM = "system", "النظام"


class Message(models.Model):
    """رسالةٌ واحدةٌ في محادثة.

    مقابلُها `haraj_chat_messages` — اثنا عشر عموداً **ثلاثةُ أزواجٍ منها
    مكرّرة**: ``message``/``message_text`` و``sender``/``sender_type``
    و``session_id``/``conversation_id``. وليس تكراراً نظريّاً: قارئُ v1
    يفحص الأعمدة في كل طلبٍ (`DESCRIBE`) ثم يبني
    ``COALESCE(NULLIF(message_text,''), NULLIF(message,''))`` — أي أن
    الشاشةَ لا تعرف أيَّ عمودٍ تقرأ حتى تسأل القاعدة.
    """

    conversation = models.ForeignKey(
        Conversation,
        verbose_name="المحادثة",
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender_kind = models.CharField(
        "نوع الكاتب", max_length=10, choices=SenderKind.choices
    )

    #: من كتبها بعينه. فارغٌ لرسائل النظام، ولرسالةِ عميلٍ بلا حساب.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="الكاتب",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages",
    )

    body = models.TextField("النص")

    #: **متى قرأها الدعمُ** — لا علمُ صفرٍ وواحد. والفرقُ ليس شكليّاً:
    #: `is_read` في v1 **لا يكتبه أحدٌ إطلاقاً** عند فتح المحادثة (فُتّش
    #: `support_panel/` كلُّه: لا تحديثَ له في أيّ ملفّ)، فشارةُ القسم تكبر
    #: ولا تصغر أبداً. ووقتُ القراءة يجيب سؤالاً ثانياً يُسأل فعلاً: «كم
    #: انتظر العميلُ قبل أن يقرأ أحد؟».
    read_at = models.DateTimeField("قُرئت", null=True, blank=True)

    created_at = models.DateTimeField("الوقت", auto_now_add=True)

    class Meta:
        verbose_name = "رسالة دعم"
        verbose_name_plural = "رسائل الدعم"
        ordering = ("id",)
        indexes = [
            models.Index(fields=["conversation", "id"], name="support_msg_thread"),
            # «غيرُ المقروء» — الشارةُ الوحيدةُ في الشاشة، ومعناها واحد.
            models.Index(
                fields=["conversation"],
                condition=Q(read_at__isnull=True, sender_kind="customer"),
                name="support_msg_unread",
            ),
        ]
        constraints = [
            # نصٌّ فارغٌ رسالةٌ لا تقول شيئاً وتدفع المحادثةَ إلى رأس القائمة.
            models.CheckConstraint(condition=~Q(body=""), name="support_msg_has_a_body"),
            # رسالةُ موظّفٍ بلا كاتبٍ تعني ردّاً لا يُعرف من كتبه — وهو أوّلُ
            # ما يُسأل عنه بعد شكوى.
            models.CheckConstraint(
                condition=~Q(sender_kind="staff") | Q(author__isnull=False),
                name="support_msg_staff_reply_has_an_author",
            ),
        ]

    def __str__(self) -> str:
        return f"رسالة #{self.pk} في محادثة #{self.conversation_id}"
