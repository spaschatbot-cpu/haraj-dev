"""Run the ledger's self-check from the command line.

Exits non-zero when anything is wrong, so it works unchanged as a CI gate, a
post-deploy step, and a nightly cron — the same check in all three places
rather than three checks that drift apart.
"""

import sys

from django.core.management.base import BaseCommand

from apps.money.verification import verify_ledger


class Command(BaseCommand):
    help = "يتحقّق من اتساق الدفتر ويُنهي برمز غير صفري عند وجود أي ملاحظة"

    def handle(self, *args, **options):
        findings = verify_ledger()

        if not findings:
            self.stdout.write(self.style.SUCCESS("الدفتر نظيف — لا ملاحظات."))
            return

        self.stdout.write(self.style.ERROR(f"الدفتر فيه {len(findings)} ملاحظة:"))
        for finding in findings:
            self.stdout.write(f"  [{finding.check}] {finding.subject}")
            self.stdout.write(f"      {finding.detail}")

        # Not CommandError: that prints a traceback-flavoured message. A cron
        # reading the exit code and an operator reading the list both want
        # exactly what is above, and nothing else.
        sys.exit(1)
