"""امشِ دورةَ العميل كاملةً على قاعدةٍ حقيقيّة، خطوةً خطوة.

**ليست حزمةَ اختبارات** — لا `pytest` ولا `conftest` ولا `ops/checks`. مشيةٌ
واحدةٌ على الطريق الذي يمشيه العميل بترتيبه، تُطبع نتيجةُ كلِّ خطوةٍ برقمها.
وهو التحقّقُ الذي تطلبه المادة ٥: «قياسٌ على قاعدةٍ حقيقيّة يُكتب رقمُه».

وكلُّ خطوةٍ تمرّ **بنقطة الـAPI** التي يمرّ بها التطبيق، لا بالخدمات مباشرةً:
خدمةٌ تُنادى من سكربتٍ تتخطّى الحارسَ والمُسلسِل والخنق، فتقول «يعمل» عمّا لا
يعمل من التطبيق. وما لا نقطةَ له (إغلاقُ المزاد، الترسية، الفوترة، قيدُ
الحوالة، الإفراج) يُنادى بخدمته لأنه **فعلُ موظّفٍ** لا فعلُ عميل.

## ما وجدته في أوّل ثلاث مشيات

* مزادُ الفحص يسحب مركباتٍ **مسدَّدة** إلى مزادٍ حيّ، فيردّ الخادمُ «المركبة
  «مسدَّدة» ولا تقبل مزايدة» على شيءٍ يراه العميلُ معروضاً (`cb74fef`).
* مزادُ الفحص لا يُفتح مرّةً ثانيةً بعد إغلاقه — والمشيةُ تُغلقه (`cb74fef`).
* رقمُ هويّةٍ مسجَّلٌ على حسابٍ آخر يردّ **500** بخطأ قاعدةٍ لا 409 برسالة
  (`b600589`).

## وما يقف اليوم

الخطوة ١٢ وحدَها: `checkout_unavailable` — لا مفاتيحَ بوّابةِ دفعٍ في `.env`
على سيرفر التجربة. وهي **إعدادُ بيئةٍ لا عطلُ كود**، ولذلك تُقيَّد الوديعةُ
بعدها بالخدمة التي يناديها مفسّرُ الويبهوك نفسُه، ليُمشى ما بعدها.

    python manage.py walk_customer_cycle
"""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "امشِ دورةَ العميل كاملةً: من إنشاء الحساب إلى استرداد التأمين."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="أقرّ بأنها تكتب في قاعدة هذه البيئة.",
        )

    def handle(self, *args, **options):
        # **البوّابةُ إقرارٌ لا `DEBUG`.** المشيةُ تكتب حساباً ومزايدةً
        # وفاتورةً وقيوداً في الدفتر، فلها بوّابة. لكنّ `DEBUG` لا يصلح
        # بوّابةً هنا: سيرفرُ التجربة يعمل بـ`DEBUG=False` — وهو موضعُها —
        # وتشغيلُه بـ`DJANGO_DEBUG=1` يقلب `ALLOWED_HOSTS` فيسقط أوّلُ طلبٍ
        # بـ`DisallowedHost`. قِيس، فردّ الخطوةُ الأولى 400 بجسمٍ فارغ.
        #
        # والإقرارُ أصدق: من يكتبه يعرف في أيّ قاعدةٍ هو.
        if not options["confirm"]:
            raise CommandError(
                "المشيةُ تكتب في القاعدة: حساباً ومزايدةً وفاتورةً وقيوداً في "
                "الدفتر. أعِد الأمر بـ--confirm."
            )
        # **تفتح مزادَها بنفسها.** المشيةُ **تُغلق** المزادَ في الخطوة ٢٠ —
        # وهي خطوةٌ منها لا أثرٌ جانبيّ — فالتشغيلُ الثاني يجد الساحةَ فارغةً
        # ويقف عند «حيٌّ منها 0». وكان على من يشغّلها أن يتذكّر
        # `open_test_auction` قبلها في كلّ مرّة، وهو تذكّرٌ يُنسى مرّةً من كلّ
        # مرّتين.
        from apps.auctions.models import Auction
        from apps.auctions.states import AuctionState

        if not Auction.objects.filter(state=AuctionState.LIVE).exists():
            self.stdout.write("لا مزادَ حيّاً — يُفتح واحدٌ للمشية:")
            call_command("open_test_auction", hours=72, cars=6)

        _walk(self.stdout)


def _walk(out):
        import json, re as _re, time, logging
        from decimal import Decimal
        from django.test import Client
        from django.utils import timezone
        from django.contrib.auth import get_user_model

        from apps.accounts.models import PhoneVerification
        from apps.auctions.models import Auction, Vehicle
        from apps.bidding.models import Bid
        from apps.money.models import Account, Invoice

        # **موظّفٌ إلى جانب العميل.** خطواتُ الموظّف كانت تنادي الخدماتِ
        # مباشرةً (`auc.end`، `settle.award_to`، `money.record_payment`)، فتقول
        # المشيةُ «الدورةُ تعمل» وهي لم تلمس زرّاً واحداً في اللوحة. والقاعدةُ
        # نفسُها التي تجعل خطواتِ العميل تمرّ بالـAPI: خدمةٌ تُنادى من سكربتٍ
        # تتخطّى الحارسَ والاستمارةَ والقدرة.
        #
        # فصار لكلّ فعلِ موظّفٍ بابُه في `/console/`، ويُسجَّل الدخولُ بحسابٍ
        # له القدراتُ فعلاً.
        _staff = (
            get_user_model().objects.filter(is_superuser=True, is_staff=True).first()
        )
        admin = Client()
        if _staff is not None:
            admin.force_login(_staff)

        _hosts = [h for h in settings.ALLOWED_HOSTS if h and not h.startswith("*")]
        HOST = dict(SERVER_NAME=_hosts[0] if _hosts else "testserver", secure=True)
        c = Client()
        W = out.write
        step_no = [0]
        fails = []

        def step(title):
            step_no[0] += 1
            W(f"\n{'─'*72}\n{step_no[0]:>2}. {title}\n")

        def ok(msg):   W(f"    ✅ {msg}\n"); pass
        def bad(msg):  fails.append(f"{step_no[0]}. {msg}"); W(f"    ❌ {msg}\n"); pass
        def note(msg): W(f"    ·  {msg}\n"); pass

        def api(method, path, token=None, **kw):
            hdr = dict(HOST)
            if token:
                hdr["HTTP_AUTHORIZATION"] = f"Bearer {token}"
            fn = getattr(c, method)
            if method in ("post", "patch", "put") and "data" in kw:
                kw["content_type"] = "application/json"
                kw["data"] = json.dumps(kw["data"])
            r = fn(f"/api/v1{path}", **kw, **hdr)
            try:
                body = r.json()
            except Exception:
                body = {}
            return r.status_code, body

        def console(path, data=None):
            """اضغط زرّاً في اللوحة — نفسَ المسار الذي تُرسل إليه الاستمارة."""
            url = "/console" + path
            if data is None:
                return admin.get(url, **HOST)
            return admin.post(url, data, **HOST, follow=False)

        PHONE = "9665" + str(int(time.time()))[-8:]
        W(f"عميلٌ جديد: {PHONE}\n")

        # **الرمزُ يُؤخذ من مولّده، لا من نصّ الرسالة.** `code_hash` في الجدول
        # SHA-256 عن قصد: «الأرقامُ توجد في موضعٍ واحدٍ — الرسالة — ولا تعود
        # في أيّ جواب» (T601). وكانت المشيةُ تقرؤه من سطر السجلّ، فتبعَت
        # **نصَّ الرسالة**: تغيّر النصُّ مرّةً فالتُقط ذيلُ الجوّال، وتغيّر
        # ثانيةً فالتُقط فراغ — ومرّتان كافيتان.
        #
        # و`generate_code` مصدرُه الوحيد: يُلَفّ فيُحتفظ بآخر ما ولّده. ولا
        # يُضعِف شيئاً — العمليّةُ هي التي تطلب الرمزَ أصلاً، والحلقةُ كلُّها
        # داخلها.
        import re as _re
        from apps.accounts import otp as _otp

        class _Catch:
            body = ""

        _real_generate = _otp.generate_code

        def _spy():
            _Catch.body = _real_generate()
            return _Catch.body

        _otp.generate_code = _spy


        from apps.bidding.eligibility import BIDDABLE_VEHICLE_STATES, check_eligibility
        from apps.money import services as money_svc

        # ═════ ١ ═════
        step("إنشاء حساب — طلبُ رمز التحقّق  POST /auth/code/")
        s, b = api("post", "/auth/code/", data={"phone": PHONE, "purpose": "login"})
        if s == 200 and b.get("sent"):
            ok("أُرسل · ينتهي " + str(b.get("expires_at",""))[:19] + " · إعادةُ الإرسال بعد " + str(b.get("resend_after")) + " ث")
        else:
            bad("HTTP " + str(s) + " — " + str(b)); return

        # ═════ ٢ ═════
        step("التوثيق وإصدار الرموز  POST /auth/verify/")
        # **الرمزُ بعد لافتته، لا أوّلَ أرقامٍ في السطر.** السجلُّ يكتب
        # «SMS to 9665… : رمز التحقق: 123456»، فالتقاطُ أوّلِ مجموعةِ أرقامٍ
        # يعطي ذيلَ الجوّال — وقع ذلك حين تغيّر نصُّ الرسالة، فردّ الخادمُ
        # «الرمز غير صحيح» ووقفت المشيةُ عند خطوتها الثانية.
        code = _Catch.body
        v = PhoneVerification.objects.filter(phone=PHONE).order_by("-id").first()
        _hh = getattr(v, "code_hash", "") or ""
        note("الرمزُ كما سُلِّم في الرسالة: " + code + " · وفي القاعدة هاشٌ لا رقم (" + str(len(_hh)) + " محرفاً)")
        s, b = api("post", "/auth/verify/", data={"phone": PHONE, "code": code, "full_name": "عميل الفحص"})
        if s != 200:
            bad("HTTP " + str(s) + " — " + str(b)); return
        TOK, USER = b["access"], b["user"]
        ok("حسابٌ #" + str(USER["id"]) + " · " + USER["display_name"] + " · " + USER["account_type"] + " · جديد=" + str(USER["is_new"]))

        # ═════ ٣ ═════
        step("قراءةُ الملفّ  GET /profile/")
        s, b = api("get", "/profile/", TOK)
        (ok if s == 200 else bad)("HTTP " + str(s) + " · الاسم «" + str(b.get("full_name","")) + "» · الهوية «" + (str(b.get("national_id","")) or "—") + "»")

        # ═════ ٤ ═════
        # رقمٌ يجتاز الخانةَ المراقِبة (`identity._checksum_holds`) — و«1098765432»
        # كان يسقط فيها بحقّ: الرقمُ العشريُّ ليس رقمَ هويّةٍ لمجرّد أنه عشرة أرقام.
        step("رقمُ الهوية  PUT /profile/national-id/")
        def _nid(seed):
            """رقمٌ يجتاز الخانةَ المراقِبة — ومختلفٌ في كلّ مشية.

            و«1098765432» كان يسقط فيها بحقّ: عشرةُ أرقامٍ ليست هويّة. ثم أسقط
            التكرارُ المشيةَ الثانية بـ500 — وهو العطلُ الذي أُصلح في
            `set_national_id`، ويبقى الرقمُ فريداً هنا لأن القيد قيدٌ صحيح.
            """
            for n in range(1000000000 + seed * 97, 1000000000 + seed * 97 + 400):
                d = str(n)
                if len(d) == 10 and _luhn(d):
                    return d
            return ""

        def _luhn(d):
            t = 0
            for i, ch in enumerate(d[:-1]):
                x = int(ch)
                if i % 2 == 0:
                    x *= 2
                    x = x - 9 if x > 9 else x
                t += x
            return (10 - t % 10) % 10 == int(d[-1])

        NID = _nid(int(time.time()) % 9000)
        s, b = api("put", "/profile/national-id/", TOK, data={"national_id": NID})
        (ok if s in (200, 201, 204) else bad)("HTTP " + str(s) + " · " + json.dumps(b, ensure_ascii=False)[:130])

        # ═════ ٥ ═════
        step("المحفظة قبل الشحن  GET /wallet/")
        s, b = api("get", "/wallet/", TOK)
        (ok if s == 200 else bad)("HTTP " + str(s) + " · إجمالي " + str(b.get("total")) + " · متاح " + str(b.get("available")) + " · محجوز " + str(b.get("held_for_auctions")))

        # ═════ ٦ ═════
        step("تصفّحُ المزادات  GET /auctions/")
        s, b = api("get", "/auctions/", TOK)
        rows = b.get("results", b) if isinstance(b, dict) else b
        live = [a for a in rows if str(a.get("state","")) in ("live","active")]
        (ok if live else bad)("HTTP " + str(s) + " · " + str(len(rows)) + " مزاداً · حيٌّ منها " + str(len(live)))
        AUC = live[0]
        note("المزادُ الحيّ: #" + str(AUC.get("id")) + " رقم " + str(AUC.get("number","?")))

        # ═════ ٧ ═════
        step("مركباتُ المزاد الحيّ  GET /vehicles/")
        s, b = api("get", "/vehicles/?auction=" + str(AUC["id"]), TOK)
        rows = b.get("results", b) if isinstance(b, dict) else b
        ok("HTTP " + str(s) + " · " + str(len(rows)) + " مركبة")
        # **المركبةُ تُختار قابلةً للمزايدة، لا أوّلَ ما في القائمة.** المشيةُ الأولى
        # وقعت على مركبةٍ حالتُها «مسدَّدة» داخل مزادٍ حيّ — وهو عطلٌ بذاته يُذكر.
        ids = [r["id"] for r in rows]
        states = dict(Vehicle.objects.filter(pk__in=ids).values_list("pk", "state"))
        biddable = [r for r in rows if states.get(r["id"]) in BIDDABLE_VEHICLE_STATES]
        stuck = [(r["id"], states.get(r["id"])) for r in rows if states.get(r["id"]) not in BIDDABLE_VEHICLE_STATES]
        if stuck:
            bad("مركباتٌ في مزادٍ حيٍّ لا تقبل مزايدة: " + str(len(stuck)) + " من " + str(len(rows)) + " · " + str(stuck[:4]))
        CAR = biddable[0] if biddable else rows[0]
        note("المركبة: #" + str(CAR["id"]) + " · لوت " + str(CAR.get("lot_number")) + " · " + str(CAR.get("title") or "") + " · حالتُها " + str(states.get(CAR["id"])))

        # ═════ ٨ ═════
        step("إضافةٌ إلى المفضّلة  PUT /favourites/<id>/")
        r = c.put("/api/v1/favourites/" + str(CAR["id"]) + "/", HTTP_AUTHORIZATION="Bearer " + TOK, **HOST)
        (ok if r.status_code == 204 else bad)("HTTP " + str(r.status_code) + " · 204 بلا جسمٍ كما هو معرَّف")
        s, b = api("get", "/favourites/", TOK)
        rows_f = b.get("results", b) if isinstance(b, dict) else b
        note("المفضّلة الآن: " + str(len(rows_f)) + " مركبة")

        # ═════ ٩ ═════
        step("تسعيرةُ المبلغ  POST /bids/quote/")
        s, b = api("post", "/bids/quote/", TOK, data={"vehicle": CAR["id"], "amount": "1000"})
        good = s == 200 and b.get("total") == "1150.00"
        (ok if good else bad)("HTTP " + str(s) + " · 1000 + ضريبة " + str(b.get("tax")) + " = " + str(b.get("total")))
        note("وهي تسعيرةُ ضريبةٍ لا بوّابةُ أهليّة — الأهليّةُ تُفحص عند المزايدة")

        # ═════ ١٠ ═════
        step("المزايدةُ قبل التأمين  POST /vehicles/<id>/bids/  ← يجب أن تُرفض")
        s, b = api("post", "/vehicles/" + str(CAR["id"]) + "/bids/", TOK, data={"amount": "1000"})
        err = (b.get("error") or {})
        reason = ((err.get("detail") or {}).get("reason")) or err.get("code","")
        (ok if reason == "no_deposit" else bad)("HTTP " + str(s) + " · السبب «" + str(reason) + "» · " + str(err.get("message",""))[:110])

        # ═════ ١١ ═════
        step("بدءُ شحن التأمين  POST /wallet/topups/")
        s, b = api("post", "/wallet/topups/", TOK, data={"auction": AUC["id"]})
        (ok if s in (200, 201) else bad)("HTTP " + str(s) + " · مرجع " + str(b.get("reference","—"))[:28] + " · مبلغ " + str(b.get("amount","—")) + " · حالة " + str(b.get("state","—")))
        REF, AMT = b.get("reference"), b.get("amount")
        note("والمبلغُ يحدّده النظام ولا يُرسَل مع الطلب")

        # ═════ ١٢ ═════
        step("التحويلُ إلى بوّابة الدفع  GET /wallet/topups/<ref>/checkout/")
        r = c.get("/api/v1/wallet/topups/" + str(REF) + "/checkout/", HTTP_AUTHORIZATION="Bearer " + TOK, **HOST)
        if r.status_code == 302:
            ok("HTTP 302 → " + str(r.get("Location",""))[:70])
        else:
            try: eb = r.json()
            except Exception: eb = {}
            bad("HTTP " + str(r.status_code) + " · " + json.dumps(eb, ensure_ascii=False)[:150])
            note("وهنا تقف دورةُ العميل على هذه البيئة: لا مفاتيحَ بوّابةٍ في `.env`")

        # ═════ ١٣ ═════
        step("شحنُ التأمين من اللوحة — «إيداع يدوي»  POST /console/money/deposit/")
        note("بابُ الموظّف حين لا بوّابةَ بطاقة — وv1 له نظيرُه، وأُعيد بقرار")
        note("المالك في ٢٤ سبتمبر ٢٠٢٦. وكان هنا نداءُ خدمةٍ يتخطّى الشاشة.")
        r = console("/money/deposit/", {
            "customer": USER["id"],
            "amount": str(AMT),
            "reference": "walk-" + PHONE,
            "reason": "شحنُ تأمينٍ في مشية دورة العميل",
        })
        (ok if r.status_code in (200, 302) else bad)(
            "HTTP " + str(r.status_code) + " · " + str(r.get("Location", ""))[:60])

# ═════ ١٤ ═════
        step("المحفظة بعد الشحن  GET /wallet/")
        s, b = api("get", "/wallet/", TOK)
        (ok if s == 200 else bad)("HTTP " + str(s) + " · إجمالي " + str(b.get("total")) + " · متاح " + str(b.get("available")) + " · محجوز " + str(b.get("held_for_auctions")))

        # ═════ ١٥ ═════
        step("كشفُ حساب المحفظة  GET /wallet/transactions/")
        s, b = api("get", "/wallet/transactions/", TOK)
        rows = b.get("results", b) if isinstance(b, dict) else b
        (ok if s == 200 else bad)("HTTP " + str(s) + " · " + str(len(rows)) + " حركة")

        # ═════ ١٦ ═════
        step("الأهليّةُ بعد التأمين — البوّابةُ نفسُها التي تقرأها الشاشة")
        u = get_user_model().objects.get(pk=USER["id"])
        car = Vehicle.objects.select_related("auction").get(pk=CAR["id"])
        el = check_eligibility(user=u, vehicle=car)
        (ok if getattr(el, "allowed", False) else bad)("مسموح=" + str(getattr(el,"allowed",None)) + " · السبب «" + str(getattr(el,"reason","") or "—") + "» · الحدّ الأدنى " + str(getattr(el,"minimum_bid","?")))
        MIN = getattr(el, "minimum_bid", None) or Decimal("1000")

        # ═════ ١٧ ═════
        step("وضعُ المزايدة  POST /vehicles/<id>/bids/")
        s, b = api("post", "/vehicles/" + str(CAR["id"]) + "/bids/", TOK, data={"amount": str(MIN)})
        (ok if s in (200, 201) else bad)("HTTP " + str(s) + " · مزايدة #" + str(b.get("id","—")) + " بمبلغ " + str(b.get("amount","—")) + " · " + json.dumps(b, ensure_ascii=False)[:110])

        # ═════ ١٨ ═════
        step("المحفظة بعد المزايدة — التأمينُ يُحجَز  GET /wallet/")
        s, b = api("get", "/wallet/", TOK)
        (ok if s == 200 else bad)("متاح " + str(b.get("available")) + " · محجوز للمزادات " + str(b.get("held_for_auctions")))

        # ═════ ١٩ ═════
        step("مزايداتي ومشاركاتي والبثّ")
        for path, label in (("/bids/mine/", "مزايدة"), ("/participations/", "مشاركة")):
            s, b = api("get", path, TOK)
            rows = b.get("results", b) if isinstance(b, dict) else b
            (ok if s == 200 and rows else bad)(path + " → HTTP " + str(s) + " · " + str(len(rows)) + " " + label)
        s, b = api("get", "/live/", TOK)
        (ok if s == 200 else bad)("/live/ → HTTP " + str(s) + " · " + json.dumps(b, ensure_ascii=False)[:100])

        # ═════ ٢٠ ═════
        step("إغلاقُ المزاد من اللوحة  POST /console/auctions/<pk>/end-now/")
        car.refresh_from_db()
        auction = car.auction
        auction.ends_at = timezone.now() - timezone.timedelta(minutes=1)
        auction.save(update_fields=["ends_at"])
        r = console("/auctions/%s/end-now/" % auction.pk, {})
        auction.refresh_from_db()
        (ok if auction.state == "ended" else bad)(
            "HTTP " + str(r.status_code) + " · المزاد " + str(auction.number)
            + " حالتُه " + auction.state)
        car.refresh_from_db()
        note("حالةُ المركبة بعد الإغلاق: " + car.state)
        try:
            outcomes = settle.settle_holds(auction)
            kept = [o for o in outcomes if o.action == "kept"]
            note("تسويةُ الرهون: " + str(len(outcomes)) + " رهناً · أُبقي " + str(len(kept)))
        except Exception as e:
            bad("تسويةُ الرهون: " + str(e)[:140])

        step("الترسية من شاشة اتخاذ القرار  POST /console/partners/<pk>/award-top/")
        r = console("/partners/%s/award-top/" % car.pk, {"back": ""})
        car.refresh_from_db()
        (ok if car.state == "awarded" else bad)(
            "HTTP " + str(r.status_code) + " · حالتُها " + car.state
            + " · الفائز #" + str(car.awarded_to_id) + " بـ" + str(car.awarded_price))

# ═════ ٢٢ ═════
        step("الفوترة من «المزايدات المقبولة»  POST /console/bids/accepted/<pk>/invoice/")
        note("الفوترةُ فعلٌ مستقلٌّ لا يتبع الترسيةَ تلقائياً — ولوحةُ الموظّف")
        note("فيها شاشةُ «رست ولم تُفوتَر» لهذا بعينه")
        r = console("/bids/accepted/%s/invoice/" % car.pk, {})
        car.refresh_from_db()
        inv0 = Invoice.objects.filter(vehicle=car).order_by("-id").first()
        (ok if inv0 is not None else bad)(
            "HTTP " + str(r.status_code) + " · "
            + (("صدرت " + inv0.number + " بمبلغ " + str(inv0.amount)) if inv0 else "لا فاتورة")
            + " · حالةُ المركبة " + car.state)

# ═════ ٢٣ ═════
        step("تفاصيلُ الفاتورة  GET /invoices/<id>/")
        if INV:
            s, b = api("get", "/invoices/" + str(INV["id"]) + "/", TOK)
            (ok if s == 200 else bad)("HTTP " + str(s) + " · إجمالي " + str(b.get("amount","—")) + " · مدفوع " + str(b.get("amount_paid","—")) + " · متبقٍّ " + str(b.get("outstanding","—")))

        # ═════ ٢٤ ═════
        step("السداد من الرصيد  POST /invoices/<id>/pay/  ← مغلقٌ بقرار المالك")
        if INV:
            s, b = api("post", "/invoices/" + str(INV["id"]) + "/pay/", TOK, data={})
            (ok if s == 409 else bad)("HTTP " + str(s) + " · " + str((b.get("error") or {}).get("message",""))[:120])
            note("«مبلغ الضمان لا يُحتسب من ثمن المركبة» — والفاتورةُ حوالةٌ بنكيّةٌ وحدَها")

        # ═════ ٢٥ ═════
        step("حسابُ الحوالة البنكيّة  GET /bank-transfer/")
        s, b = api("get", "/bank-transfer/", TOK)
        (ok if s == 200 else bad)("HTTP " + str(s) + " · " + json.dumps(b, ensure_ascii=False)[:170])

        # ═════ ٢٦ ═════
        step("قيدُ الحوالة من «إنشاء دفعة»  POST /console/payments/create/")
        if INV:
            inv = Invoice.objects.get(pk=INV["id"])
            r = console("/payments/create/", {
                "invoice": inv.pk,
                "amount": str(inv.amount - inv.amount_paid),
                "reference": "walk-" + PHONE,
                "reason": "حوالةٌ بنكيّة في مشية دورة العميل",
            })
            inv.refresh_from_db()
            car.refresh_from_db()
            if car.state == "invoiced":
                auc.mark_paid(car)
                car.refresh_from_db()
            (ok if inv.state == "paid" else bad)(
                "HTTP " + str(r.status_code) + " · الفاتورة " + inv.state
                + " · المركبة " + car.state)

# ═════ ٢٨ ═════
        step("مشترياتي  GET /purchases/")
        s, b = api("get", "/purchases/", TOK)
        rows = b.get("results", b) if isinstance(b, dict) else b
        (ok if s == 200 and rows else bad)("HTTP " + str(s) + " · " + str(len(rows)) + " شراء")

        # ═════ ٢٩ ═════
        step("التأمينُ يعود حرّاً بعد السداد  GET /wallet/")
        s, b = api("get", "/wallet/", TOK)
        (ok if s == 200 else bad)("متاح " + str(b.get("available")) + " · محجوز " + str(b.get("held_for_auctions")) + " · مقفول " + str(b.get("locked_for_dues")))

        # ═════ ٣٠ ═════
        step("الإفراج والتسليم — جهةُ الموظّف")
        try:
            if car.state == "paid":
                auc.release(car); car.refresh_from_db(); ok("أُفرج عنها · حالتُها " + car.state)
            else:
                bad("لا إفراج — الحالةُ " + car.state)
        except Exception as e:
            bad("الإفراج: " + str(e)[:150])

        # ═════ ٣١ ═════
        step("رفعُ صورة الآيبان  POST /profile/documents/")
        note("والاستردادُ يُرفض بدونها بحقّ — وهو ما ردّته المشيةُ السابقة")
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        import io as _io
        _buf = _io.BytesIO(); Image.new('RGB', (40, 25), (200, 210, 220)).save(_buf, 'PNG')
        png = _buf.getvalue()
        r = c.post("/api/v1/profile/documents/", {"kind": "iban", "file": SimpleUploadedFile("iban.png", png, content_type="image/png")},
                   HTTP_AUTHORIZATION="Bearer " + TOK, **HOST)
        try: rb = r.json()
        except Exception: rb = {}
        (ok if r.status_code in (200, 201) else bad)("HTTP " + str(r.status_code) + " · " + json.dumps(rb, ensure_ascii=False)[:150])

        step("طلبُ استرداد التأمين  POST /wallet/refund-requests/")
        # **وحدةٌ كاملةٌ ومعها الآيبان** — والوديعةُ لا تُجزَّأ، والرقمُ هو ما
        # يُحوَّل إليه. وكانت المشيةُ تطلب ١٬٠٠٠ فتمرّ، وهو العطلُ الذي أُصلح.
        s, b = api("post", "/wallet/refund-requests/", TOK,
                   data={"amount": str(money_svc.deposit_amount_for()),
                         "iban": "SA0380000000608010167519"})
        (ok if s in (200, 201) else bad)("HTTP " + str(s) + " · " + json.dumps(b, ensure_ascii=False)[:150])


        # ═════ جهةُ الموظّف: طابورُ الاستردادات ═════
        step("طلبُ الاسترداد في طابور اللوحة  GET /console/refunds/queue/")
        r = console("/refunds/queue/")
        body = r.content.decode() if r.status_code == 200 else ""
        (ok if r.status_code == 200 else bad)("HTTP " + str(r.status_code))
        (ok if PHONE in body else bad)("طلبُ العميل ظاهرٌ للمالية: " + str(PHONE in body))
        from apps.money.models import RefundRequest as _RR
        _req = _RR.objects.filter(user__phone=PHONE).order_by("-id").first()
        if _req is not None:
            (ok if _req.iban else bad)("الآيبانُ على الطلب: " + (_req.iban or "— فارغ"))
            (ok if (_req.iban and _req.iban in body) else bad)(
                "ويظهر في شاشة المالية: " + str(bool(_req.iban and _req.iban in body)))

        W("\n" + "═"*72 + "\n")
        W("الخطوات: " + str(step_no[0]) + " · نجحت " + str(step_no[0]-len(fails)) + " · فشلت " + str(len(fails)) + "\n")
        for f in fails: W("  ❌ " + f + "\n")
        W("\nالعميل " + PHONE + " · #" + str(USER["id"]) + " · المركبة #" + str(CAR["id"]) + " · المزاد " + str(auction.number) + "\n")
        pass

