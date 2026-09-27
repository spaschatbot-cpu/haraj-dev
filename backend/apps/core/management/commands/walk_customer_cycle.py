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
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "امشِ دورةَ العميل كاملةً: من إنشاء الحساب إلى استرداد التأمين."

    def handle(self, *args, **options):
        # يكتب حساباً ومزايدةً وفاتورةً وقيوداً في الدفتر. وبيئةُ الإنتاج
        # ليست موضعَ مشيةٍ تجريبيّة — كما في `open_test_auction`.
        if not settings.DEBUG:
            raise CommandError(
                "مشيةُ دورة العميل لا تعمل خارج DEBUG: تكتب حساباً ومزايدةً "
                "وفاتورةً وقيوداً في الدفتر."
            )
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

        HOST = dict(SERVER_NAME="haraj.spas.sa", secure=True)
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

        PHONE = "9665" + str(int(time.time()))[-8:]
        W(f"عميلٌ جديد: {PHONE}\n")

        # **الرمزُ يُلتقط من حيث يُسلَّم، لا من القاعدة.** `code_hash` في الجدول
        # SHA-256 عن قصد: «الأرقامُ توجد في موضعٍ واحدٍ — الرسالة — ولا تعود في أيّ
        # جواب» (T601). وفي بيئة التجربة `SMS_BACKEND=console_backend` يكتبها في
        # السجلّ، فيُلتقط السطرُ نفسُه هنا. وقراءةُ العمود كانت تعطي الهاشَ فيُردّ
        # بـ«لا تتجاوز 8 حروف» — وهو الحارسُ يعمل، لا عطل.
        import logging, re as _re
        class _Catch(logging.Handler):
            body = ''
            def emit(self, record):
                a = record.args or ()
                _Catch.body = str(a[1]) if len(a) > 1 else record.getMessage()
        _lg = logging.getLogger('apps.accounts.sms')
        _lg.addHandler(_Catch()); _lg.setLevel(logging.INFO)


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
        _m = _re.search(r"[0-9]{4,8}", _Catch.body)
        code = _m.group(0) if _m else ""
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
        step("قيدُ التأمين — بديلٌ عن البوّابة الغائبة")
        note("ليس طريقَ عميل: البوّابةُ غيرُ مضبوطةٍ هنا، فيُقيَّد المبلغُ بالخدمة")
        note("التي يناديها مفسّرُ الويبهوك نفسُه، ليُمشى ما بعده")
        u = get_user_model().objects.get(pk=USER["id"])
        try:
            money_svc.credit_payment(user=u, amount=Decimal(str(AMT)), source="card",
                                     reference=REF, memo="مشيةُ دورة العميل")
            ok("قُيّد " + str(AMT))
        except Exception as e:
            bad("تعذّر القيد: " + str(e)[:170])

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
        step("إغلاقُ المزاد — جهةُ الموظّف")
        from apps.auctions import services as auc
        from apps.bidding import settlement as settle
        car.refresh_from_db(); auction = car.auction
        auction.ends_at = timezone.now() - timezone.timedelta(minutes=1)
        auction.save(update_fields=["ends_at"])
        try:
            auc.end(auction); ok("أُغلق المزاد " + str(auction.number) + " · حالتُه " + auction.state)
        except Exception as e:
            bad("الإغلاق: " + str(e)[:140])
        car.refresh_from_db(); note("حالةُ المركبة بعد الإغلاق: " + car.state)
        try:
            outcomes = settle.settle_holds(auction)
            kept = [o for o in outcomes if o.action == "kept"]
            note("تسويةُ الرهون: " + str(len(outcomes)) + " رهناً · أُبقي " + str(len(kept)))
        except Exception as e:
            bad("تسويةُ الرهون: " + str(e)[:140])

        # ═════ ٢١ ═════
        step("الترسية — جهةُ الموظّف")
        try:
            top = Bid.objects.live().filter(vehicle=car).order_by("-amount").first()
            settle.award_to(car, bidder=top.bidder, price=top.amount)
            car.refresh_from_db()
            ok("رستْ على #" + str(top.bidder_id) + " بمبلغ " + str(top.amount) + " · حالتُها " + car.state)
        except Exception as e:
            bad("الترسية: " + str(e)[:160])

        # ═════ ٢٢ ═════
        step("إصدارُ الفاتورة — جهةُ الموظّف")
        note("الفوترةُ فعلٌ مستقلٌّ لا يتبع الترسيةَ تلقائياً — ولوحةُ الموظّف")
        note("فيها شاشةُ «رست ولم تُفوتَر» لهذا بعينه")
        try:
            car.refresh_from_db()
            # **`settlement.invoice_award` لا `money.issue_invoice` مباشرةً.** الأولى
            # تنقل رهنَ المزايدة إلى قفلٍ على الفاتورة (`lock_for_invoice`) في
            # المعاملة نفسِها؛ والثانية تُصدر الفاتورةَ وحدَها. ومشيةٌ سابقةٌ نادت
            # الثانيةَ فبقي تأمينُ العميل **محجوزاً للمزاد** بعد سدادٍ كاملٍ وإفراج،
            # ووقف طلبُ الاسترداد. كان خطأَ المشية لا خطأَ المنتج — ويُكتب هنا لأن
            # من يقرأ السكربتَ لاحقاً سيسأل لماذا لا تُنادى الأقصرُ.
            inv0 = settle.invoice_award(car); car.refresh_from_db()
            ok("صدرت " + inv0.number + " بمبلغ " + str(inv0.amount) + " · حالةُ المركبة " + car.state)
        except Exception as e:
            bad("الفوترة: " + str(e)[:170])


        step("فاتورةُ الفوز  GET /invoices/")
        s, b = api("get", "/invoices/", TOK)
        rows = b.get("results", b) if isinstance(b, dict) else b
        INV = rows[0] if rows else None
        if INV:
            ok("HTTP " + str(s) + " · " + str(len(rows)) + " فاتورة · #" + str(INV.get("id")) + " رقم " + str(INV.get("number","—")) + " · إجمالي " + str(INV.get("amount","—")) + " · حالة " + str(INV.get("state","—")))
        else:
            dbi = Invoice.objects.filter(vehicle=car).first()
            bad("لا فاتورةَ في الـAPI · وفي القاعدة: " + (dbi.number if dbi else "لا شيء"))

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
        step("قيدُ الحوالة — جهةُ الموظّف")
        if INV:
            try:
                inv = Invoice.objects.get(pk=INV["id"])
                money_svc.record_payment(invoice=inv, amount=inv.amount - inv.amount_paid, source="cash",
                                         reference="cycle-" + PHONE)
                if car.state == "invoiced":
                    auc.mark_paid(car)
                inv.refresh_from_db(); ok("قُيّدت " + str(inv.amount) + " · حالةُ الفاتورة " + inv.state)
            except Exception as e:
                bad("القيد: " + str(e)[:170])

        # ═════ ٢٧ ═════
        step("الفاتورةُ والمركبةُ بعد السداد")
        if INV:
            s, b = api("get", "/invoices/" + str(INV["id"]) + "/", TOK)
            (ok if s == 200 else bad)("HTTP " + str(s) + " · حالة " + str(b.get("state","—")) + " · متبقٍّ " + str(b.get("outstanding","—")))
        car.refresh_from_db(); note("حالةُ المركبة: " + car.state)

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
        s, b = api("post", "/wallet/refund-requests/", TOK, data={"amount": "1000"})
        (ok if s in (200, 201) else bad)("HTTP " + str(s) + " · " + json.dumps(b, ensure_ascii=False)[:150])

        W("\n" + "═"*72 + "\n")
        W("الخطوات: " + str(step_no[0]) + " · نجحت " + str(step_no[0]-len(fails)) + " · فشلت " + str(len(fails)) + "\n")
        for f in fails: W("  ❌ " + f + "\n")
        W("\nالعميل " + PHONE + " · #" + str(USER["id"]) + " · المركبة #" + str(CAR["id"]) + " · المزاد " + str(auction.number) + "\n")
        pass

