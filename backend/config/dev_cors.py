"""ترويسات CORS لمعاينةٍ محليّة — **بيئة التطوير وحدها**.

لماذا هنا لا `django-cors-headers`: الحاجة واحدةٌ ومؤقّتة — تشغيلُ تطبيق
Flutter في متصفّح على منفذٍ آخر لمعاينة الشاشات على جهازٍ بلا محاكٍ أندرويد.
حزمةٌ كاملةً في `pyproject.toml` من أجل ترويستين تُقرأ لاحقاً كأنها قرارُ
معماريةٍ للإنتاج، وهي ليست كذلك: النشرُ المقصود يمرّ بوكيلٍ شفّاف على أصلٍ
واحد (`T1029`)، فلا CORS فيه أصلاً.

**لا يُستورَد إلا من `settings/dev.py`.** استيرادُه في `prod` أو `test` يفتح
الأصولَ المسموحة على قيمةٍ كُتبت للمعاينة — ولذلك القائمة صريحةٌ محدودة ولا
نجمةَ فيها، ولا `Allow-Credentials`: كوكي الجلسة لا يعبر من هنا.
"""

from django.utils.deprecation import MiddlewareMixin

# الأصول المسموحة صراحةً. `localhost` و`127.0.0.1` أصلان مختلفان في المتصفح
# رغم أنهما جهازٌ واحد، فيُذكَران معاً وإلا حُجب النداء بحسب ما كتبه المطوّر.
_ALLOWED_ORIGINS = frozenset(
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in ("3000", "5000", "5050", "8080")
)


class DevCorsMiddleware(MiddlewareMixin):
    """يردّ على `OPTIONS` ويضع الترويسات لأصلٍ مذكورٍ في القائمة وحده."""

    def process_request(self, request):
        # طلبُ الاستطلاع لا يصل إلى العرض: DRF يردّ عليه 405 فيفشل النداء
        # الحقيقيّ قبل أن يُرسَل.
        if request.method == "OPTIONS" and "HTTP_ORIGIN" in request.META:
            from django.http import HttpResponse

            return HttpResponse(status=204)
        return None

    def process_response(self, request, response):
        origin = request.META.get("HTTP_ORIGIN")
        if origin in _ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, Accept, Accept-Language, "
                "X-Requested-With, Idempotency-Key"
            )
            response["Access-Control-Max-Age"] = "600"
            # الأصلُ يدخل في اختيار النسخة المخبَّأة، وإلا خدم الكاشُ استجابةً
            # بترويسةِ أصلٍ آخر.
            response["Vary"] = (
                f"{response['Vary']}, Origin" if response.has_header("Vary") else "Origin"
            )
        return response
