"""يعرض نسخةَ الويب من التطبيق ويحوّل `/api/` إلى الخادم المحلي — من أصلٍ واحد.

لماذا وسيط: الخادمُ بلا CORS (لا `django-cors-headers` ولا إعدادُه)، فتطبيقُ
الويب على `localhost:8090` لا يستطيع أن ينادي `127.0.0.1:8001` — المتصفّحُ يرفض
قبل أن يصل الطلب. وفتحُ CORS على الخادم لأجل معاينةٍ محلّيّة يفتحه للإنتاج
أيضاً. فهنا أصلٌ واحد: الملفّاتُ الثابتة من `build/web`، و`/api/` تُمرَّر كما هي.

للمعاينة على هذا الجهاز وحدَه — لا يُنشَر، ولا يُستعمل أمام شبكة.

    flutter build web --pwa-strategy=none --dart-define=HARAJ_API_BASE_URL=http://localhost:8090
    python tool/serve_web_with_api.py            # 8090 ← build/web + 127.0.0.1:8001
    python tool/serve_web_with_api.py https://haraj.spas.sa   # على خادم التطوير

**والصورُ تمرّ من هنا أيضاً** (`/media/`): الخادمُ يكتب روابطها مطلقةً على أصله،
وFlutter على الويب يجلب الصورة بـ`fetch` فيحتاج CORS لا يرسله الخادم — فكانت
صورُ السيّارات لا تُرسم. فتُعاد كتابةُ أصلِ الخادم في ردود JSON إلى هذا الأصل،
وتُمرَّر `/media/` كما تُمرَّر `/api/`.
"""

from __future__ import annotations

import http.server
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PORT = int(os.environ.get("PORT", "8090"))
#: الخادم: وسيطٌ أوّل على سطر الأمر، ثمّ `BACKEND`، ثمّ المحلّي.
BACKEND = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BACKEND", "http://127.0.0.1:8001")).rstrip("/")
ROOT = Path(__file__).resolve().parent.parent / "build" / "web"

#: ترويساتٌ لا تُمرَّر: تخصّ الاتّصالَ نفسَه لا الطلب.
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "host"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(BACKEND + self.path, data=body, method=self.command)
        for name, value in self.headers.items():
            # بلا `Accept-Encoding`: ردٌّ مضغوطٌ لا تُعاد كتابةُ روابط صوره.
            if name.lower() not in HOP and name.lower() != "accept-encoding":
                request.add_header(name, value)
        try:
            response = urllib.request.urlopen(request, timeout=60)
            status, headers, payload = response.status, response.headers, response.read()
        except urllib.error.HTTPError as refusal:
            status, headers, payload = refusal.code, refusal.headers, refusal.read()
        if "json" in (headers.get("Content-Type") or ""):
            # `PUBLIC_ORIGIN` حين يقف أمام هذا الوسيط وسيطٌ آخر (خادمُ `flutter
            # run` في `dev_web.py`): الصورةُ تُطلب من الأصل الذي يراه المتصفّح.
            here = os.environ.get("PUBLIC_ORIGIN") or f"http://{self.headers.get('Host', f'localhost:{PORT}')}"
            payload = payload.replace(f"{BACKEND}/media/".encode(), f"{here}/media/".encode())
        self.send_response(status)
        for name, value in headers.items():
            if name.lower() not in HOP and name.lower() != "content-length":
                self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _route(self) -> None:
        if self.path.startswith(("/api/", "/media/")):
            return self._proxy()
        # تطبيقُ صفحةٍ واحدة: كلُّ مسارٍ ليس ملفّاً يعود إلى index.html.
        if not (ROOT / self.path.lstrip("/").split("?")[0]).is_file():
            self.path = "/index.html"
        return super().do_GET()

    do_GET = _route  # noqa: N815

    def end_headers(self) -> None:
        # **لا كاش للملفّات الثابتة**: كلُّ بناءٍ جديدٍ يُرى بتحديث الصفحة. كان
        # المتصفّحُ يُعيد `main.dart.js` القديم فيبدو التعديلُ كأنه لم يُرفع —
        # «عايز التعديلات تظهر مباشرة» (المالك، ٢٩ سبتمبر ٢٠٢٦).
        if not self.path.startswith(("/api/", "/media/")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):  # noqa: N802
        return self._proxy()

    do_PUT = do_PATCH = do_DELETE = do_POST  # noqa: N815


if __name__ == "__main__":
    if not ROOT.is_dir() and not os.environ.get("PUBLIC_ORIGIN"):
        sys.exit(f"لا بناءَ في {ROOT} — شغّل flutter build web أوّلاً.")
    print(f"http://localhost:{PORT}  ←  {ROOT}  +  /api → {BACKEND}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
