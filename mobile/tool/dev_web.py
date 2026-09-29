"""يشغّل التطبيقَ في كروم مربوطاً بخادم التطوير، ويعيد تحميله عند كلّ حفظ.

طلبُ المالك (٢٩ سبتمبر ٢٠٢٦): «أيّ تحديث في الكود يظهر في التطبيق مباشرةً، مش
أعمل كلّ شويّة بيلد». كان كلُّ تعديلٍ يعني `flutter build web` (دقيقتان) ثمّ
تحديثَ الصفحة. وهنا `flutter run -d chrome` — مترجِمُ التطوير يحمل التعديلَ
في ثوانٍ — ومراقبٌ على `lib/` يرسل إليه `r` (hot reload) عند حفظ ملفّ دارت،
و`R` (إعادة تشغيل) حين يتغيّر `pubspec.yaml` أو الأصول، فلا ضغطةَ على شيء.

والطريقُ إلى الخادم ثلاثُ حلقات:

    كروم ← flutter run :8090 ← (web_dev_config.yaml: /api/ و/media/)
         ← serve_web_with_api.py :8091 ← https://haraj.spas.sa

الحلقةُ الوسطى لأن الخادمَ يكتب روابطَ الصور مطلقةً على أصله بلا CORS،
وFlutter على الويب يجلب الصورة بـ`fetch` — فتُعاد كتابتُها إلى أصل الصفحة.

    python tool/dev_web.py                         # على haraj.spas.sa
    python tool/dev_web.py http://127.0.0.1:8001   # على الخادم المحلي

للمعاينة على هذا الجهاز وحدَه — لا يُنشَر.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # mobile/
BACKEND = sys.argv[1] if len(sys.argv) > 1 else "https://haraj.spas.sa"
APP_PORT = 8090
PROXY_PORT = 8091

#: ما يكفيه hot reload، وما يحتاج إعادةَ تشغيل (الأصولُ والاعتماديّاتُ لا تُحمَّل ساخنةً).
RELOAD = (HERE / "lib",)
RESTART = (HERE / "pubspec.yaml", HERE / "assets", HERE / "web")


def snapshot(paths: tuple[Path, ...]) -> dict[Path, float]:
    seen: dict[Path, float] = {}
    for root in paths:
        files = [root] if root.is_file() else (p for p in root.rglob("*") if p.is_file())
        for path in files:
            try:
                seen[path] = path.stat().st_mtime
            except OSError:
                pass
    return seen


def watch(flutter: subprocess.Popen[str]) -> None:
    """كلَّ نصف ثانية: ما تغيّر؟ وبعد هدوءٍ قصير يُرسَل الأمر — حفظُ عدّة ملفّاتٍ
    معاً (تنسيقٌ أو إعادةُ تسمية) يعطي تحميلاً واحداً لا عشرة."""
    reload_seen, restart_seen = snapshot(RELOAD), snapshot(RESTART)
    pending = ""
    quiet_since = 0.0
    while flutter.poll() is None:
        time.sleep(0.5)
        now_reload, now_restart = snapshot(RELOAD), snapshot(RESTART)
        if now_restart != restart_seen:
            pending, quiet_since = "R", time.time()
        elif now_reload != reload_seen and pending != "R":
            pending, quiet_since = "r", time.time()
        reload_seen, restart_seen = now_reload, now_restart
        if pending and time.time() - quiet_since > 0.6:
            label = "إعادة تشغيل" if pending == "R" else "تحميل ساخن"
            print(f"\n[dev_web] تغيّر ملف ← {label}", flush=True)
            try:
                assert flutter.stdin is not None
                flutter.stdin.write(pending)
                flutter.stdin.flush()
            except (OSError, ValueError):
                return
            pending = ""


def relay(flutter: subprocess.Popen[str]) -> None:
    """يطبع خرجَ flutter كما هو، ويعيد التشغيلَ حين يُرفض التحميلُ الساخن.

    التحميلُ الساخن لا يقبل تغييراً في بنية صنفٍ ثابت (حقلٌ يُحذف أو يُضاف)،
    فيطبع «Hot reload rejected… Try performing a hot restart». وكان ذلك يترك
    التطبيقَ على النسخة القديمة حتى يُضغط R باليد — وهو ما طُلب ألّا يكون.
    """
    assert flutter.stdout is not None
    for line in flutter.stdout:
        print(line, end="", flush=True)
        if "Hot reload rejected" in line or "Try performing a hot restart" in line:
            print("[dev_web] التحميل الساخن رُفض ← إعادة تشغيل", flush=True)
            try:
                assert flutter.stdin is not None
                flutter.stdin.write("R")
                flutter.stdin.flush()
            except (OSError, ValueError):
                return


def main() -> None:
    proxy = subprocess.Popen(
        [sys.executable, str(HERE / "tool" / "serve_web_with_api.py"), BACKEND],
        env={**os.environ, "PORT": str(PROXY_PORT), "PUBLIC_ORIGIN": f"http://localhost:{APP_PORT}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    print(f"[dev_web] الوسيط :{PROXY_PORT} ← {BACKEND}", flush=True)

    flutter = subprocess.Popen(
        [
            "flutter", "run", "-d", "chrome",
            "--web-port", str(APP_PORT),
            f"--dart-define=HARAJ_API_BASE_URL=http://localhost:{APP_PORT}",
            # نافذةٌ بمقاس هاتف: التطبيقُ مصمَّمٌ لعرض ٣٩٠ تقريباً.
            "--web-browser-flag=--window-size=440,940",
        ],
        cwd=HERE,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        # `flutter` على ويندوز ملفُّ bat — لا يُشغَّل إلا عبر الصدفة.
        shell=os.name == "nt",
    )
    threading.Thread(target=watch, args=(flutter,), daemon=True).start()
    threading.Thread(target=relay, args=(flutter,), daemon=True).start()
    try:
        flutter.wait()
    except KeyboardInterrupt:
        pass
    finally:
        proxy.terminate()
        if flutter.poll() is None:
            flutter.terminate()


if __name__ == "__main__":
    main()
