"""Importing and exporting vehicles from the console. T806.

This file is a screen, not a rule. Every column, every conversion and every
rejection reason lives in `apps.auctions.importexport`, which the phase-005
tests already exercise on a hundred bad rows. What is added here is the three
things only a screen can get wrong:

* **The export is the import's input.** One writer (`apps.core.sheets`) produces
  both, so a file downloaded from this page uploads again without an edit and
  changes nothing. `test_a_download_uploads_again_and_changes_no_row` is that
  round trip, and it is T806's acceptance criterion.
* **Every rejected row is named.** v1 stopped after five and said "and 95 more
  errors", so a file went round the office one fix at a time. The rejections
  come back as a **sheet the operator can work from**, not as a paragraph.
* **A dry run exists.** An operator uploading four hundred rows into production
  wants to see what would happen before it does. Nothing else in v1 had one, and
  the way people compensated was to upload ten rows at a time.
"""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.auctions.importexport import export_vehicles, import_vehicles
from apps.auctions.models import Vehicle
from apps.auctions.visibility import visible_vehicles
from apps.core import audit

from .views import console_page

#: What one upload may carry. A file larger than this is a mistake — a
#: spreadsheet of the whole fleet, an image someone renamed — and reading it
#: into memory to discover that is how a console falls over.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@console_page("console:vehicles-export")
def export(request):
    """Download the current filter's cars as a real `.xlsx` (I5).

    The filter is honoured rather than ignored: an operator who searched for one
    auction's cars and pressed export wants those cars. v1 exported everything
    every time, so the file was useless and people copied rows out of the screen
    by hand.
    """
    rows = visible_vehicles(request.user).select_related("auction", "owner_company")

    auction = request.GET.get("auction")
    if auction and auction.isdigit():
        rows = rows.filter(auction__number=int(auction))

    state = request.GET.get("state")
    if state:
        rows = rows.filter(state=state)

    payload = export_vehicles(rows.order_by("auction_id", "lot_number"))
    stamp = timezone.now().strftime("%Y%m%d-%H%M")

    response = HttpResponse(
        payload,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="vehicles-{stamp}.xlsx"'
    return response


@console_page("console:vehicles-import")
def upload(request):
    """Upload a sheet, or preview what one would do.

    A dry run applies nothing and reports everything. It is the same code path
    as the real thing — `import_vehicles` inside a transaction that is rolled
    back — because a preview that runs different code is a preview of a
    different thing.
    """
    if request.method != "POST":
        return render(request, "console/vehicles_import.html", {"report": None})

    uploaded = request.FILES.get("sheet")
    if uploaded is None:
        messages.error(request, "اختر ملفاً أولاً.")
        return redirect("console:vehicles-import")

    if uploaded.size > MAX_UPLOAD_BYTES:
        messages.error(
            request,
            f"الملف أكبر من الحدّ ({MAX_UPLOAD_BYTES // (1024 * 1024)} ميجابايت).",
        )
        return redirect("console:vehicles-import")

    dry_run = bool(request.POST.get("dry_run"))
    data = uploaded.read()

    try:
        report = _run(data, dry_run=dry_run)
    except Exception as failure:
        # A file that is not a sheet at all — a PDF renamed, a corrupt upload.
        # Named rather than raised: the operator can fix a file, and a 500 tells
        # them nothing about which one.
        messages.error(request, f"تعذّرت قراءة الملف: {failure}")
        return redirect("console:vehicles-import")

    if not dry_run and report.changed:
        # One entry per car, not one per upload.
        #
        # `record()` refuses an entry with no subject, and it is right to: an
        # audit row that names no row cannot answer the question an audit
        # actually asks, which is "who last touched *this* car". A single
        # summary entry would leave every imported car with no trace at all,
        # and a partner asking why their lot changed would be told to go and
        # read an upload log.
        #
        # The reason and the batch's own numbers are carried on every entry, so
        # the upload is still reconstructable — by grouping on the note rather
        # than by having a row of its own.
        reason = (request.POST.get("reason") or "").strip() or "استيراد مركبات"
        batch = {
            "created": len(report.created),
            "updated": len(report.updated),
            "rejected": len(report.rejections),
        }
        touched = Vehicle.objects.filter(pk__in=report.created + report.updated)
        for vehicle in touched:
            audit.record(
                action="console.import_vehicles",
                entity=vehicle,
                actor=request.user,
                after={
                    **audit.snapshot(vehicle, ["lot_number", "make", "model", "year"]),
                    "batch": batch,
                },
                note=reason,
            )

    return render(
        request,
        "console/vehicles_import.html",
        {"report": report, "dry_run": dry_run},
    )


def _run(data: bytes, *, dry_run: bool):
    """Apply the sheet, or apply it and undo it.

    The dry run rolls back rather than skipping the writes, so what it reports
    is what would actually have happened — including a rejection that only the
    database could produce, like a lot number that collides with a row this
    same file created two lines earlier.
    """
    from django.db import transaction

    if not dry_run:
        return import_vehicles(data)

    class _Rollback(Exception):
        pass

    holder = {}
    try:
        with transaction.atomic():
            holder["report"] = import_vehicles(data)
            raise _Rollback
    except _Rollback:
        pass
    return holder["report"]


@console_page("console:vehicles-import-errors")
def rejections(request):
    """The rejected rows, as a sheet.

    A hundred bad rows produce a hundred reasons, and an operator fixes them in
    the file they already have rather than reading them off a screen. The report
    is rebuilt from a re-run of the same upload — see the template: the file is
    posted again rather than held in a session, because a session holding a
    five-megabyte spreadsheet is a session that falls over.
    """
    uploaded = request.FILES.get("sheet")
    if request.method != "POST" or uploaded is None:
        return redirect("console:vehicles-import")

    report = _run(uploaded.read(), dry_run=True)

    response = HttpResponse(
        report.to_sheet().to_xlsx(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = 'attachment; filename="rejections.xlsx"'
    return response


__all__ = ["MAX_UPLOAD_BYTES", "export", "rejections", "upload"]
