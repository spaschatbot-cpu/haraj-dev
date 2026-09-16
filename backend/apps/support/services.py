"""كلُّ كتابةٍ في محادثةِ دعم تمرّ من هنا. T924.

بابٌ واحدٌ لا خمسة، وهو نفسُ قرار :mod:`apps.bidding.settlement` و
:func:`apps.money.services.post`: في v1 خمسةُ أفعالٍ في ملفٍّ واحد
(`conversation_action.php`) كلُّ واحدٍ منها يكتب بيده — فردُّ الموظّف يُدرج
صفّاً، والإغلاقُ يُحدّث عموداً، والتحويلُ يُعيد كتابة أعمدةٍ في جدولٍ ثانٍ،
ولا يمرّ أيٌّ منها على الآخر. ونتيجةُ ذلك مقيسةٌ في دَمب الإنتاج:

* **٩٣٬٢٩٤ محادثةً من ٩٣٬٢٩٥ ما زالت «مفتوحة»** — أي أن زرَّ الإغلاق ضُغط
  **مرّةً واحدة** في تسعة أشهر. ولا شيء في الشيفرة يُغلق محادثةً بالتقادم.
* **٨٢٬١٨٠ رسالةً `is_read = 0`** — ولا سطرَ في `support_panel/` كلِّه
  يكتب `is_read = 1` عند فتح المحادثة. فالشارةُ الحمراء تكبر ولا تصغر.
* **صفرُ ردٍّ من موظّف**: العمودُ `sender` في ٩٣٬٢٦١ رسالةً قيمتاه
  `bot` (٩٢٬٠٩٤) و`user` (١٬١٦٧) — و`agent` **لا وجود لها**، وهي القيمةُ
  التي يكتبها زرُّ الردّ. أي أن الزرَّ لم ينجح مرّةً واحدة.

فالأفعالُ هنا خمسةٌ كذلك، غير أن كلَّ واحدٍ منها يترك **قيدَ تدقيقٍ باسم
فاعله وسببه**، وثلاثةٌ منها تمرّ على :func:`post_message` — فالمحادثةُ التي
حُوِّلت أو أُغلقت تقول ذلك في نصِّها، لا في عمودٍ يراه الموظّفُ وحده.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.core import audit
from apps.core.errors import DomainError

from .models import Conversation, Department, Message, SenderKind

__all__ = [
    "SupportError",
    "assign",
    "close",
    "mark_read",
    "post_message",
    "reopen",
    "reply",
    "start_conversation",
    "transfer",
]

#: ما يُصوَّر في `AuditLog` من المحادثة. لا `last_message_at`: يتغيّر مع كل
#: رسالة، وسطرُ «قبل/بعد» يحمله يُغرق القيدَ بتغييرٍ لم يقرّره أحد.
CONVERSATION_FIELDS = (
    "department_id",
    "assigned_to_id",
    "closed_at",
    "closed_by_id",
    "closed_reason",
)


class SupportError(DomainError):
    """فعلٌ على محادثةٍ رُفض — والرفضُ جوابٌ يُقرأ، لا خطأُ برنامج."""

    code = "support_error"
    default_message = "تعذّر تنفيذ الفعل على هذه المحادثة."


def start_conversation(
    *,
    department: Department,
    customer=None,
    guest_name: str = "",
    language: str = "ar",
) -> Conversation:
    """يفتح محادثةً جديدة — ويرفض قسماً أغلق بابه.

    v1 لا يفحص `is_online` عند البدء إطلاقاً: العلمُ يُعرَض في اللوحة وتُقلَب
    قيمتُه بزرّ، ولا قارئَ له في مسار العميل. فالقسمُ «المعطَّل» يستقبل كما
    كان، والموظّفُ الذي أطفأه يظنّ أنه أغلق الباب.
    """
    if not department.is_open:
        raise SupportError(
            f"department {department.code} is closed",
            user_message=f"قسم «{department.name_ar}» لا يستقبل محادثاتٍ الآن.",
            detail={"department": department.code},
        )
    if customer is None and not guest_name.strip():
        raise SupportError(
            "a conversation needs a customer or a guest name",
            user_message="لا يمكن فتحُ محادثةٍ بلا اسم.",
        )
    return Conversation.objects.create(
        department=department,
        customer=customer,
        guest_name=guest_name.strip()[:190],
        language=language[:2] or "ar",
    )


@transaction.atomic
def post_message(
    *,
    conversation: Conversation,
    sender_kind: str,
    body: str,
    author=None,
) -> Message:
    """يكتب رسالةً — **وهو الموضعُ الوحيد الذي يلمس `last_message_at`**.

    والقفلُ على المحادثة قبل التحديث: رسالتان تصلان معاً (العميلُ يكتب
    والموظّفُ يردّ في اللحظة نفسها) تقرآن العمودَ معاً وتكتبان فوقه، فيبقى
    فيه **الأقدم** — والمحادثةُ تنزل في القائمة كلَّما زاد الكلامُ فيها.
    """
    text = (body or "").strip()
    if not text:
        raise SupportError("empty message body", user_message="لا تُرسَل رسالةٌ بلا نصّ.")
    if sender_kind == SenderKind.STAFF and author is None:
        raise SupportError(
            "a staff message must name its author",
            user_message="ردُّ الموظّف يُكتب باسمه.",
        )

    # `select_for_update` على الصفّ لا على الجدول: الطابورُ هنا طابورُ
    # محادثةٍ واحدة، ورسالتان في محادثتين مختلفتين لا تنتظر إحداهما الأخرى.
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    message = Message.objects.create(
        conversation=locked,
        sender_kind=sender_kind,
        author=author,
        body=text,
        # رسالةُ الموظّفِ مقروءةٌ لحظةَ كتابتها: «غيرُ المقروء» هنا يعني
        # «لم يقرأه الدعمُ بعد»، وردُّ الدعم لا ينتظر نفسَه.
        read_at=timezone.now() if sender_kind != SenderKind.CUSTOMER else None,
    )
    locked.last_message_at = message.created_at
    locked.save(update_fields=["last_message_at"])
    conversation.last_message_at = message.created_at
    return message


def mark_read(*, conversation: Conversation, staff) -> int:
    """يختم رسائلَ العميل غيرَ المقروءة — ويُرجع كم ختم.

    **وv1 لا يفعل هذا إطلاقاً.** فُتّش `support_panel/` كلُّه: لا تحديثَ
    لـ`is_read` في أيّ ملفّ، فالعمودُ يُكتب صفراً عند الإدراج ويبقى. وشارةُ
    القسم — التي تقرأ `is_read = 0` — تعدّ اليوم **٨٢٬١٨٠** رسالة.

    ولا قيدَ تدقيقٍ على الفتح: القراءةُ ليست قراراً، وقيدٌ لكلّ فتحِ محادثةٍ
    يُغرق السجلَّ الذي تُقرأ فيه القرارات.
    """
    return conversation.messages.filter(
        sender_kind=SenderKind.CUSTOMER, read_at__isnull=True
    ).update(read_at=timezone.now())


@transaction.atomic
def reply(
    *, conversation: Conversation, staff, body: str, close_reason: str = ""
) -> Message:
    """ردُّ موظّفٍ على محادثة، ويُغلقها بعده إن سُمّي سببُ الإغلاق.

    **ولا تقييمَ مع الردّ.** استمارةُ v1 تحمل قائمةً منسدلةً يختار منها
    **الموظّفُ نفسُه** تقييمَ خدمته (وخياراتُها ثلاثةٌ: ٥ و٤ و٣ — لا ١ ولا
    ٢)، فتُكتب في `haraj_chat_ratings` كأنها رأيُ العميل. والجدولُ فيه
    **صفٌّ واحدٌ** في تسعة أشهر، فلا بياناتٍ تُفقَد بتركه. والتقييمُ حين
    يُبنى يكتبه العميلُ من تطبيقه.
    """
    if not conversation.is_open:
        raise SupportError(
            "conversation is closed",
            user_message="المحادثةُ مغلقة — أعِد فتحَها قبل الردّ.",
        )
    message = post_message(
        conversation=conversation,
        sender_kind=SenderKind.STAFF,
        author=staff,
        body=body,
    )
    # الردُّ يقرأ ما قبله: من فتح المحادثةَ وردّ فقد قرأ ما فيها، وترْكُ
    # رسائلها «غيرَ مقروءة» يُبقي الشارةَ الحمراء على محادثةٍ أُجيب عنها.
    mark_read(conversation=conversation, staff=staff)
    audit.record(
        action="console.support_reply",
        entity=conversation,
        actor=staff,
        after={"message_id": message.pk, "length": len(message.body)},
        note=close_reason or "",
    )
    if close_reason:
        close(conversation=conversation, staff=staff, reason=close_reason)
    return message


@transaction.atomic
def close(*, conversation: Conversation, staff, reason: str) -> Conversation:
    """يُغلق محادثةً بسببٍ مكتوب — والسببُ إلزاميّ.

    v1 يكتب `closed_at = NOW()` ولا شيء غيرَه: لا من أغلق ولا لماذا. والعميلُ
    الذي يعود ليسأل «لماذا أُغلقت محادثتي؟» لا جوابَ له في الصفّ، ولا في
    سجلٍّ — لأن لا سجلّ.
    """
    text = (reason or "").strip()
    if not text:
        raise SupportError("closing needs a reason", user_message="اكتب سببَ الإغلاق.")
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    if not locked.is_open:
        raise SupportError("already closed", user_message="المحادثةُ مغلقةٌ أصلاً.")
    before = audit.snapshot(locked, CONVERSATION_FIELDS)
    locked.closed_at = timezone.now()
    locked.closed_by = staff
    locked.closed_reason = text[:255]
    locked.save(update_fields=["closed_at", "closed_by", "closed_reason"])
    audit.record(
        action="console.support_close",
        entity=locked,
        actor=staff,
        before=before,
        after=audit.snapshot(locked, CONVERSATION_FIELDS),
        note=text,
    )
    # والعميلُ يقرأ أنها أُغلقت في نصِّ المحادثة نفسِه، لا في عمودٍ لا يراه.
    post_message(
        conversation=locked,
        sender_kind=SenderKind.SYSTEM,
        body=f"أُغلقت المحادثة — {text}",
    )
    conversation.refresh_from_db()
    return conversation


@transaction.atomic
def reopen(*, conversation: Conversation, staff, reason: str) -> Conversation:
    """يُعيد فتحَ محادثةٍ أُغلقت. **ولا مقابلَ لها في v1 إطلاقاً.**

    هناك الإغلاقُ طريقٌ باتّجاهٍ واحد، فالعميلُ الذي أُغلقت محادثتُه خطأً
    يبدأ محادثةً جديدةً بلا تاريخها — وهو أحدُ أسباب أن ٩٣ ألفَ صفٍّ تعود
    إلى ٣٬٩٣٢ اسماً فقط.
    """
    text = (reason or "").strip()
    if not text:
        raise SupportError(
            "reopening needs a reason", user_message="اكتب سببَ إعادة الفتح."
        )
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    if locked.is_open:
        raise SupportError("already open", user_message="المحادثةُ مفتوحةٌ أصلاً.")
    before = audit.snapshot(locked, CONVERSATION_FIELDS)
    locked.closed_at = None
    locked.closed_by = None
    locked.closed_reason = ""
    locked.save(update_fields=["closed_at", "closed_by", "closed_reason"])
    audit.record(
        action="console.support_reopen",
        entity=locked,
        actor=staff,
        before=before,
        after=audit.snapshot(locked, CONVERSATION_FIELDS),
        note=text,
    )
    post_message(
        conversation=locked,
        sender_kind=SenderKind.SYSTEM,
        body=f"أُعيد فتحُ المحادثة — {text}",
    )
    conversation.refresh_from_db()
    return conversation


@transaction.atomic
def transfer(
    *, conversation: Conversation, staff, department: Department, reason: str
) -> Conversation:
    """ينقل المحادثةَ إلى قسمٍ آخر — **ولا يلمس رسائلَها**.

    v1 ينقل ثم يُنفّذ ``UPDATE haraj_chat_messages SET department_code = ?
    WHERE conversation_id = ?`` — أي **يُعيد كتابةَ تاريخها**: رسائلُ العميل
    التي وصلت «خدمةَ العملاء» تصير كأنها وصلت «الماليّة»، فتقريرُ حجمِ عملِ
    القسم يتغيّر بأثرٍ رجعيّ بضغطة. والعمودُ نفسُه **فارغٌ في ٨١٬٣٢٤ رسالةً
    من ٩٣٬٢٦١** — أي أنه يُعيد كتابةَ عمودٍ لا يُملأ أصلاً.

    فلا عمودَ قسمٍ على الرسالة هنا: قسمُها قسمُ محادثتها **وقتَ وصولها**،
    وهذا ما يقوله سطرُ النظام الذي يُكتب في النصّ عند النقل.
    """
    text = (reason or "").strip()
    if not text:
        raise SupportError("a transfer needs a reason", user_message="اكتب سببَ التحويل.")
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    if locked.department_id == department.pk:
        raise SupportError(
            "same department",
            user_message=f"المحادثةُ في «{department.name_ar}» أصلاً.",
        )
    before = audit.snapshot(locked, CONVERSATION_FIELDS)
    was = locked.department.name_ar
    locked.department = department
    # التحويلُ يرفع الإسناد: المُسنَدُ إليه من القسم الأوّل، وبقاؤه يعني
    # محادثةً في قسمٍ ومسؤولاً في قسمٍ آخر.
    locked.assigned_to = None
    locked.save(update_fields=["department", "assigned_to"])
    audit.record(
        action="console.support_transfer",
        entity=locked,
        actor=staff,
        before=before,
        after=audit.snapshot(locked, CONVERSATION_FIELDS),
        note=text,
    )
    post_message(
        conversation=locked,
        sender_kind=SenderKind.SYSTEM,
        body=f"حُوِّلت المحادثة من «{was}» إلى «{department.name_ar}» — {text}",
    )
    conversation.refresh_from_db()
    return conversation


@transaction.atomic
def assign(*, conversation: Conversation, staff, assignee) -> Conversation:
    """يُسند المحادثةَ إلى موظّف، أو يرفع الإسناد بـ``assignee=None``.

    v1 يُسند إلى صفٍّ في `haraj_chat_staff` — جدولِ الموظّفين الثاني — ثم
    **لا يعرض العمودَ في أيّ شاشة**. وقيمتُه في الدَمب: `staff_id` فارغٌ في
    ٩٣٬٢٩٤ صفّاً من ٩٣٬٢٩٥.
    """
    locked = Conversation.objects.select_for_update().get(pk=conversation.pk)
    before = audit.snapshot(locked, CONVERSATION_FIELDS)
    locked.assigned_to = assignee
    locked.save(update_fields=["assigned_to"])
    audit.record(
        action="console.support_assign",
        entity=locked,
        actor=staff,
        before=before,
        after=audit.snapshot(locked, CONVERSATION_FIELDS),
        note=str(assignee) if assignee is not None else "رفعُ الإسناد",
    )
    conversation.refresh_from_db()
    return conversation
