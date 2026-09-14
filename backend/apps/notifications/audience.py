"""من يصله البثّ — مرشّحاتٌ تُعَدّ **قبل** الزرّ لا بعده. T832.

عطلُ v1 مكتوبٌ في مكانٍ واحد: خيارُ `all_users` هو **أوّلُ عنصرٍ في القائمة
المنسدلة**، أي المختارُ افتراضياً؛ واستعلامُه `SELECT id, player_id, fcm_token
FROM userss` بلا `WHERE` ولا `LIMIT`. فعنوانٌ ونصٌّ وضغطةٌ واحدة = بثٌّ إلى
القاعدة كلِّها، بلا عدٍّ مسبقٍ ولا تأكيد. والعددُ يظهر **بعد** التنفيذ في جملة
النجاح: «تم تنفيذ الإشعار الجماعي لعدد N مستخدم».

فهنا يُقلَب الترتيب: الجمهورُ **يُوصَف ثمّ يُعَدّ ثمّ يُعرَض**، والزرُّ آخرُ
الخطوات. ومن يرى «٤٤٬٠٣٦ مستلماً» قبل أن يضغط يتصرّف غيرَ من يرى زرّاً وحده.

ولماذا وحدةٌ مستقلّةٌ لا استعلامٌ في المنظر
==========================================
لأن المرشّح يُنفَّذ **مرّتين**: مرّةً في الطلب ليُعَدّ ويُعرَض، ومرّةً في
المهمّة المؤجَّلة لتُدرَج الصفوف. ونسختان من الشرط في موضعين هما كيف يُعرَض
عددٌ ويُرسَل إلى غيره.

والموظّفون خارج كلّ جمهور
=========================
`is_staff=False` في الأساس ولا خيار يرفعه: البثُّ خطابٌ إلى العملاء، وحسابُ
موظّفٍ يصله إشعارُ «مزادٌ يبدأ غداً» ضجيجٌ في أحسن الأحوال — وفي أسوئها رسالةٌ
نصّيّةٌ مدفوعة إلى جوّالِ من يجلس في المكتب.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

#: نوعُ الحساب: كلٌّ، أو فردٌ، أو منشأة.
ACCOUNT_TYPES = (("", "كل الأنواع"), ("individual", "أفراد"), ("company", "منشآت"))

#: حالةُ الحساب. ثلاثُ حالاتٍ يفرّقها البثُّ فعلاً:
#:
#: * `active` — يفتح التطبيق ويزايد. الجمهورُ الطبيعيّ.
#: * `banned` — محظورٌ الآن (`banned_until` في المستقبل). يُذكر لأن رسالةَ
#:   «انتهى حظرك» أو «راجِع المالية» تُرسَل إليه هو بالذات.
#: * `unverified` — سجّل ولم يوثّق جوّاله. و**رسالةٌ نصّيّةٌ إلى جوّالٍ لم
#:   يُوثَّق إنفاقٌ على رقمٍ لا نعرف أنه لصاحبه**، فالشاشة تسمّيه ليُقصد لا
#:   ليُشمل بالصدفة.
STATUSES = (
    ("", "كل الحالات"),
    ("active", "نشط"),
    ("banned", "محظور الآن"),
    ("unverified", "جوّاله غير موثّق"),
)

#: علاقةٌ بمزادٍ بعينه — والفرقُ بين الاثنين فرقُ نيّة:
#:
#: * `bidders` — من زايد فيه فعلاً. الأقربُ إلى «يهمّه هذا المزاد».
#: * `favourites` — من وضع سيارةً منه في مفضّلته. وهو جمهورُ التذكير قبل
#:   الانطلاق (`auctions.services.queue_auction_reminder`)، لأنه أقربُ ما
#:   يقوله العميلُ بنفسه عن نيّته قبل أن تبدأ المزايدة.
AUCTION_LINKS = (
    ("", "أيّ علاقة"),
    ("bidders", "من زايد في المزاد"),
    ("favourites", "من وضع سيارةً منه في مفضّلته"),
)


@dataclass(frozen=True)
class Audience:
    """وصفُ جمهورٍ — قابلٌ للتخزين في `Broadcast.audience` وإعادةِ التنفيذ."""

    account_type: str = ""
    status: str = ""
    auction_id: int | None = None
    auction_link: str = ""
    #: من عليه فاتورةٌ مفتوحةٌ أو مسدَّدةٌ جزئيّاً.
    with_dues: bool = False

    @classmethod
    def from_request(cls, data) -> Audience:
        """اقرأ المرشّحَ من استمارةٍ — وما ليس خياراً معروفاً **يُهمَل**.

        يُهمَل ولا يُفرِغ النتيجة: قيمةٌ غريبةٌ في الطلب يجب أن تُقرأ «لا
        مرشّح» لا «لا أحد»، وإلّا صار الطريقُ إلى بثٍّ بلا مرشّحٍ هو كتابةَ
        حرفٍ خطأ. (والعكس — «لا مرشّح» تعني القاعدة كلَّها — محروسٌ بالعدّ
        المعروض وبالتأكيد فوق الحدّ، لا بابتلاع القيم.)
        """
        known_types = {value for value, _ in ACCOUNT_TYPES if value}
        known_status = {value for value, _ in STATUSES if value}
        known_links = {value for value, _ in AUCTION_LINKS if value}

        raw_auction = (data.get("auction") or "").strip()
        auction_id = int(raw_auction) if raw_auction.isdigit() else None
        link = (data.get("auction_link") or "").strip()
        return cls(
            account_type=(
                data.get("account_type", "").strip()
                if data.get("account_type", "").strip() in known_types
                else ""
            ),
            status=(
                data.get("status", "").strip()
                if data.get("status", "").strip() in known_status
                else ""
            ),
            auction_id=auction_id,
            # علاقةٌ بلا مزادٍ لا معنى لها، ومزادٌ بلا علاقةٍ معناه «من زايد
            # فيه» — وهو المعنى الذي يقصده من يكتب رقم مزاد.
            auction_link=(link if link in known_links else "bidders")
            if auction_id
            else "",
            with_dues=str(data.get("with_dues", "")).strip() in ("1", "on", "true"),
        )

    def as_dict(self) -> dict:
        return {
            "account_type": self.account_type,
            "status": self.status,
            "auction_id": self.auction_id,
            "auction_link": self.auction_link,
            "with_dues": self.with_dues,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Audience:
        data = data or {}
        return cls(
            account_type=data.get("account_type", "") or "",
            status=data.get("status", "") or "",
            auction_id=data.get("auction_id") or None,
            auction_link=data.get("auction_link", "") or "",
            with_dues=bool(data.get("with_dues")),
        )

    # -- الاستعلام ---------------------------------------------------------

    def queryset(self) -> QuerySet:
        """العملاءُ الذين يطابقون هذا الوصف، بلا تكرار.

        `distinct()` ليست تزييناً: الوصلُ إلى `bids` يعطي صفّاً لكلّ مزايدة —
        ومزايدٌ زايد ثلاثين مرّةً في مزادٍ واحد كان سيُعَدّ ثلاثين مستلماً
        ويتلقّى ثلاثين رسالة. وهو خطأٌ يُقرأ في الفاتورة لا على الشاشة.
        """
        rows = get_user_model().objects.filter(is_staff=False)

        if self.account_type:
            rows = rows.filter(account_type=self.account_type)

        now = timezone.now()
        if self.status == "active":
            rows = rows.filter(is_active=True).filter(
                Q(banned_until__isnull=True) | Q(banned_until__lte=now)
            )
        elif self.status == "banned":
            rows = rows.filter(banned_until__gt=now)
        elif self.status == "unverified":
            rows = rows.filter(phone_verified_at__isnull=True)

        if self.auction_id:
            if self.auction_link == "favourites":
                rows = rows.filter(favourites__vehicle__auction_id=self.auction_id)
            else:
                rows = rows.filter(bids__vehicle__auction_id=self.auction_id)

        if self.with_dues:
            from apps.money.models import UNPAID_INVOICE_STATES

            rows = rows.filter(invoices__state__in=list(UNPAID_INVOICE_STATES))

        return rows.distinct()

    def count(self) -> int:
        return self.queryset().count()

    def describe(self) -> str:
        """الجملةُ التي تُعرَض بجوار العدد — وتُحفَظ في الصفّ كما قُرئت."""
        parts: list[str] = []
        labels = dict(ACCOUNT_TYPES)
        if self.account_type:
            parts.append(labels[self.account_type])
        if self.status:
            parts.append(dict(STATUSES)[self.status])
        if self.auction_id:
            link = dict(AUCTION_LINKS).get(self.auction_link, "من زايد في المزاد")
            parts.append(f"{link} رقم {self.auction_id}")
        if self.with_dues:
            parts.append("عليه مستحقّات غير مسدَّدة")
        if not parts:
            # **لا تُسمَّى «الكلّ» بكلمةٍ محايدة.** «كل العملاء» تُقرأ اختياراً،
            # وهذه حالةُ من لم يختر شيئاً — وهي بالضبط الحالةُ التي كانت في v1
            # افتراضيّةً بضغطة.
            return "كل العملاء — بلا أيّ مرشّح"
        return " · ".join(parts)


__all__ = ["ACCOUNT_TYPES", "AUCTION_LINKS", "STATUSES", "Audience"]
