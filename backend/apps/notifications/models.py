"""Outbound messages to customers — SMS, push, and in-app.

Every send is recorded before it is attempted, so "did he get the message?" has
an answer, and a provider outage looks like a queue rather than like silence.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    SMS = "sms", "رسالة نصية"
    PUSH = "push", "إشعار"
    IN_APP = "in_app", "داخل التطبيق"


class DeliveryState(models.TextChoices):
    QUEUED = "queued", "في الطابور"
    SENT = "sent", "أُرسل"
    DELIVERED = "delivered", "وصل"
    FAILED = "failed", "فشل"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications"
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    template = models.CharField(max_length=64)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)

    state = models.CharField(
        max_length=16, choices=DeliveryState.choices, default=DeliveryState.QUEUED
    )
    provider_reference = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["state", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel} → {self.user_id} ({self.state})"


class Device(models.Model):
    """One handset a customer receives push notifications on. T620.

    **The owner is set from the caller's token, never from a request body.** In
    v1 the client sent the account id alongside the push token, so registering
    somebody else's handset was a form field away — and the alerts that go out
    on this channel say what a person is bidding on and for how much.

    The token is unique across the whole table rather than per user, and that is
    the interesting constraint: a handset that changes hands re-registers with
    the *same* provider token under a new account, and without this the previous
    owner would keep receiving the new one's bid alerts. Re-registration moves
    the row instead of adding one.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices"
    )

    #: What the push provider calls this handset. A credential for sending to
    #: it, so it is never returned in a response — see the serializer.
    token = models.CharField(max_length=255, unique=True)

    platform = models.CharField(
        max_length=16,
        choices=[("android", "أندرويد"), ("ios", "آي أو إس"), ("web", "ويب")],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"], name="device_user_recent"),
        ]

    def __str__(self) -> str:
        return f"{self.platform} · {self.user_id}"

    @property
    def token_tail(self) -> str:
        """The last six characters, enough to tell two handsets apart on a screen."""
        return self.token[-6:]


class BroadcastState(models.TextChoices):
    PENDING = "pending", "في الطابور"
    RUNNING = "running", "قيد الإدراج"
    DONE = "done", "أُدرج"
    FAILED = "failed", "فشل"


class Broadcast(models.Model):
    """رسالةٌ واحدةٌ قرّر إنسانٌ أن تذهب إلى جمهور — **والصفُّ هو القرار**. T832.

    v1 لا يملك هذا الصفّ إطلاقاً: `notifications` هناك صفٌّ لكلّ **مستلم**، بلا
    `sent_by` ولا `campaign_id` ولا `channel` — فشاشة `/notifications/log`
    تُجيب «من استلم» ولا تُجيب أبداً **«من أرسل»**. وبثُّ `all_users` عبر
    topic في FCM لا يترك أثراً قابلاً للعدّ أصلاً: عددُ المستلمين الحقيقيّ
    مشتركو الـtopic، وهو رقمٌ لا يعرفه النظام.

    والبثُّ الذي لا يُسجَّل لا يُسأل عنه أحد. فهذا الصفُّ يُكتب **قبل** أن
    يُدرَج إشعارٌ واحد، ويحمل: من، وماذا، وإلى كم، وبأيّ قناة، وبأيّ كلفةٍ
    مقدَّرة، وكم دخل الطابور فعلاً.

    ولماذا `recipient_count` عمودٌ مخزَّنٌ لا يُحسب عند القراءة
    =========================================================
    لأنه **الرقمُ الذي رآه الموظّف قبل أن يضغط**. مرشّحُ «من عليه مستحقّات»
    يعطي عدداً مختلفاً بعد أسبوع، وسؤالُ ما بعد الحادث هو «كم قال له الزرّ؟»
    لا «كم يعطي المرشّح اليوم؟».
    """

    #: قناةٌ واحدةٌ للبثّ الواحد — ولا تُخلط قناتان في صفّ. الفرقُ بينهما
    #: مالٌ: `in_app` صفٌّ في جدولنا لا يكلّف هللة، و`sms` يُحاسَب بالرسالة.
    #: وبثٌّ «يذهب بكلّ القنوات» يجعل الكلفة غير قابلة للعرض قبل الزرّ.
    channel = models.CharField(max_length=16, choices=Channel.choices)

    title = models.CharField(max_length=120, blank=True)
    body = models.TextField()

    #: المرشّح كما اختاره الموظّف — يُعاد تنفيذُه في المهمّة المؤجَّلة.
    audience = models.JSONField(default=dict, blank=True)
    #: الجملةُ العربيّة التي وُصف بها الجمهور على الشاشة، محفوظةً كما قُرئت.
    audience_label = models.CharField(max_length=300, blank=True)

    #: كم مستلماً عُدَّ **وعُرض** قبل الضغط. انظر رأس الصنف.
    recipient_count = models.PositiveIntegerField(default=0)

    #: كلفةُ الرسالة الواحدة وقتَ البثّ، ومجموعُها. **NULL تعني «لا يُعرف»**
    #: لا «صفر»: `SMS_COST_PER_MESSAGE` بلا قيمةٍ افتراضيّة، ورقمٌ مخترَعٌ في
    #: شاشةِ إنفاق أسوأُ من فراغٍ يقول إنه فراغ.
    unit_cost = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    estimated_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    #: مفتاحُ التفرُّد — النمطُ نفسُه الذي يحرس المال في `apps.money.services`.
    #: يُشتقّ من هويّة الحدث (الرمزُ الذي مُنح في شاشة المعاينة)، فضغطتان على
    #: «إرسال» أو إعادةُ تحميلٍ بعد `POST` تصطدمان بهذا القيد ولا تصيران بثّين.
    idempotency_key = models.CharField(max_length=120, unique=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="broadcasts",
    )
    #: السببُ الذي كتبه الموظّف. يدخل `AuditLog` معه.
    reason = models.TextField(blank=True)

    state = models.CharField(
        max_length=16, choices=BroadcastState.choices, default=BroadcastState.PENDING
    )
    #: كم صفَّ إشعارٍ دخل الطابور فعلاً، وكم تعذّر. يملؤهما التنفيذُ المؤجَّل.
    queued_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="broadcast_recent"),
            models.Index(fields=["state", "created_at"], name="broadcast_state"),
        ]

    def __str__(self) -> str:
        return f"{self.channel} → {self.recipient_count} ({self.state})"
