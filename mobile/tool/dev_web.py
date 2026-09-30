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


#: كم ينتظر التحميلُ قبل أن يُعَدّ عالقاً. أبطأُ إعادة تشغيلٍ قِيست هنا ٩ ثوانٍ.
STUCK_AFTER = 60.0

#: ما يطبعه flutter حين ينتهي أمرٌ أُرسل إليه — نجاحاً أو بلا نافذةٍ متّصلة.
DONE_MARKS = ("Reloaded application", "Restarted application", "Recompile complete", "Reloaded ")


class Runner:
    """flutter run واحدٌ حيّ، يُعاد إطلاقُه إن علق.

    **لماذا الحارس** (٣٠ سبتمبر ٢٠٢٦): علق تحميلٌ ساخن على «Performing hot
    reload...» ولم ينتهِ، وكلُّ حفظٍ بعده أُرسل إلى عمليّةٍ لا تسمع — فبقي
    التطبيقُ على نسخةٍ قديمة والمالكُ يظنّ أن التعديلات تحتاج «بيلد». فالآن:
    أمرٌ لم ينتهِ خلال دقيقة يُسقط العمليّةَ كلَّها ويُطلقها من جديد.
    """

    def __init__(self) -> None:
        self.flutter: subprocess.Popen[str] | None = None
        self.sent_at = 0.0
        self.busy = False
        # لا أمرَ قبل أن يقول flutter «جاهز»: الإقلاعُ الأوّل دقيقتان، وأمرٌ فيه
        # يُعَدّ عالقاً فيُسقَط الإقلاعُ نفسُه — وقع أوّلَ مرّة.
        self.ready = False
        self.opened = False
        self.lock = threading.Lock()

    def launch(self) -> None:
        self.flutter = subprocess.Popen(
            [
                # **`web-server` لا `chrome`** (٣٠ سبتمبر ٢٠٢٦): مع `chrome`
                # لا يصل التحميلُ إلا إلى النافذة التي فتحها flutter بنفسه، فإن
                # أُغلقت أو فُتح التطبيقُ في تبويبٍ عاديّ طبع «No client
                # connected» وبقيت الشاشةُ قديمة — وقع. ومع `web-server` كلُّ
                # تبويبٍ يفتح المنفذَ يتّصل ويصله التحميل.
                "flutter", "run", "-d", "web-server",
                "--web-port", str(APP_PORT),
                "--web-hostname", "localhost",
                f"--dart-define=HARAJ_API_BASE_URL=http://localhost:{APP_PORT}",
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
        self.busy = False
        self.ready = False
        threading.Thread(target=self.relay, args=(self.flutter,), daemon=True).start()

    def kill(self) -> None:
        flutter = self.flutter
        if flutter is None or flutter.poll() is not None:
            return
        if os.name == "nt":
            # الشجرةُ كلُّها: flutter.bat ← dart ← كروم التصحيح.
            subprocess.run(
                ["taskkill", "/PID", str(flutter.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            flutter.terminate()

    def send(self, command: str) -> None:
        flutter = self.flutter
        if flutter is None or flutter.poll() is not None:
            return
        with self.lock:
            try:
                assert flutter.stdin is not None
                flutter.stdin.write(command)
                flutter.stdin.flush()
                self.sent_at, self.busy = time.time(), True
            except (OSError, ValueError):
                pass

    def relay(self, flutter: subprocess.Popen[str]) -> None:
        """يطبع خرجَ flutter، ويعيد التشغيلَ حين يُرفض التحميلُ الساخن.

        التحميلُ الساخن لا يقبل تغييراً في بنية صنفٍ ثابت، فيطبع «Hot reload
        rejected… Try performing a hot restart» ويترك النسخةَ القديمة.
        """
        assert flutter.stdout is not None
        for line in flutter.stdout:
            print(line, end="", flush=True)
            if "Flutter run key commands" in line:
                self.ready = True
                if not self.opened:
                    self.opened = True
                    open_app()
            if any(mark in line for mark in DONE_MARKS):
                self.busy = False
            if "Hot reload rejected" in line or "Try performing a hot restart" in line:
                print("[dev_web] التحميل الساخن رُفض ← إعادة تشغيل", flush=True)
                self.send("R")


def open_app() -> None:
    """يفتح التطبيقَ في كروم بنافذةٍ بمقاس هاتف — مرّةً عند أوّل جاهزيّة.

    بمسار كروم الصريح: `start chrome` وحده لم يفتح شيئاً على هذا الجهاز، فبقي
    flutter يطبع «No client connected» ولا نافذةَ تستقبل التحميل.
    """
    url = f"http://localhost:{APP_PORT}/"
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    chrome = next((path for path in candidates if path.is_file()), None)
    if chrome is None:
        import webbrowser

        webbrowser.open(url)
        return
    subprocess.Popen([str(chrome), "--new-window", "--window-size=440,940", f"--app={url}"])


def watch(runner: Runner) -> None:
    """كلَّ نصف ثانية: ما تغيّر؟ وبعد هدوءٍ قصير يُرسَل الأمر — حفظُ عدّة ملفّاتٍ
    معاً (تنسيقٌ أو إعادةُ تسمية) يعطي تحميلاً واحداً لا عشرة. **ولا يُرسَل أمرٌ
    فوق أمرٍ لم ينتهِ**؛ ينتظر، والحارسُ يفكّ العالق."""
    reload_seen, restart_seen = snapshot(RELOAD), snapshot(RESTART)
    pending = ""
    quiet_since = 0.0
    while True:
        time.sleep(0.5)
        now_reload, now_restart = snapshot(RELOAD), snapshot(RESTART)
        if now_restart != restart_seen:
            pending, quiet_since = "R", time.time()
        elif now_reload != reload_seen and pending != "R":
            pending, quiet_since = "r", time.time()
        reload_seen, restart_seen = now_reload, now_restart

        if runner.busy and time.time() - runner.sent_at > STUCK_AFTER:
            print("[dev_web] التحميل علق أكثر من دقيقة ← إعادة إطلاق flutter", flush=True)
            runner.kill()
            runner.launch()
            pending = ""
            continue

        if pending and runner.ready and not runner.busy and time.time() - quiet_since > 0.6:
            label = "إعادة تشغيل" if pending == "R" else "تحميل ساخن"
            print(f"[dev_web] تغيّر ملف ← {label}", flush=True)
            runner.send(pending)
            pending = ""


def main() -> None:
    proxy = subprocess.Popen(
        [sys.executable, str(HERE / "tool" / "serve_web_with_api.py"), BACKEND],
        env={**os.environ, "PORT": str(PROXY_PORT), "PUBLIC_ORIGIN": f"http://localhost:{APP_PORT}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    print(f"[dev_web] الوسيط :{PROXY_PORT} ← {BACKEND}", flush=True)

    runner = Runner()
    runner.launch()
    threading.Thread(target=watch, args=(runner,), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        proxy.terminate()
        runner.kill()


if __name__ == "__main__":
    main()
