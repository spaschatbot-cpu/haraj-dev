"""Every error leaves the API in the same shape, with the right status code.

The views below exist only for this file. They are mounted through
``ROOT_URLCONF`` pointing at this module, so the assertions go through the real
DRF dispatch — the handler is exercised the way a request exercises it, not
called directly with a hand-built context.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from apps.core.exceptions import MESSAGES, code_for, envelope
from apps.money.services import InsufficientFunds, MoneyError, Unbalanced


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_money_error(request):
    raise MoneyError("nothing free to lock against this invoice")


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_insufficient_funds(request):
    from apps.money.models import Account, AccountKind

    account = Account(kind=AccountKind.INSURANCE_FREE, balance=Decimal("0.00"))
    raise InsufficientFunds(account, Decimal("10000.00"))


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_not_found(request):
    raise NotFound()


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_permission_denied(request):
    raise PermissionDenied()


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_validation_error(request):
    raise ValidationError({"amount": ["مبلغ غير صالح"]})


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_unexpected(request):
    raise RuntimeError("the database password is hunter2 and the disk is on fire")


urlpatterns = [
    path("boom/money", raise_money_error),
    path("boom/funds", raise_insufficient_funds),
    path("boom/missing", raise_not_found),
    path("boom/forbidden", raise_permission_denied),
    path("boom/invalid", raise_validation_error),
    path("boom/unexpected", raise_unexpected),
]

pytestmark = pytest.mark.urls(__name__)


@pytest.fixture
def api():
    return APIClient(raise_request_exception=False)


def assert_envelope(body):
    """Every response carries exactly these three keys under ``error``."""
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "detail"}
    assert isinstance(body["error"]["code"], str) and body["error"]["code"]
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["detail"] is not None


class TestMoneyIsAConflictNotAFailure:
    def test_a_refused_money_operation_is_409(self, api):
        response = api.get("/boom/money")
        assert response.status_code == 409
        assert_envelope(response.json())
        assert response.json()["error"]["code"] == "money_error"
        assert response.json()["error"]["message"] == MESSAGES["money_error"]

    def test_a_subclass_carries_its_own_code_and_arabic_message(self, api):
        response = api.get("/boom/funds")
        assert response.status_code == 409
        body = response.json()
        assert_envelope(body)
        assert body["error"]["code"] == "insufficient_funds"
        assert body["error"]["message"] == "الرصيد المتاح لا يكفي"

    def test_the_diagnostic_english_never_reaches_the_client(self, api):
        body = api.get("/boom/funds").json()
        assert "insurance_free" not in str(body)
        assert "needs" not in str(body)

    def test_the_code_is_derived_from_the_class_name(self):
        assert code_for(Unbalanced("x")) == "unbalanced"
        assert code_for(MoneyError("x")) == "money_error"


class TestDrfExceptionsKeepTheirStatus:
    def test_not_found_is_404(self, api):
        response = api.get("/boom/missing")
        assert response.status_code == 404
        assert_envelope(response.json())
        assert response.json()["error"]["code"] == "not_found"
        assert response.json()["error"]["message"] == "غير موجود"

    def test_permission_denied_is_403(self, api):
        response = api.get("/boom/forbidden")
        assert response.status_code == 403
        assert_envelope(response.json())
        assert response.json()["error"]["code"] == "permission_denied"

    def test_validation_errors_land_in_detail(self, api):
        response = api.get("/boom/invalid")
        assert response.status_code == 400
        body = response.json()
        assert_envelope(body)
        assert body["error"]["code"] == "invalid"
        assert body["error"]["detail"] == {"amount": ["مبلغ غير صالح"]}


class TestTheUnexpected:
    def test_an_unhandled_exception_is_500_in_the_same_shape(self, api):
        response = api.get("/boom/unexpected")
        assert response.status_code == 500
        assert_envelope(response.json())
        assert response.json()["error"]["code"] == "internal_error"

    def test_it_returns_an_incident_id_and_nothing_else(self, api):
        body = api.get("/boom/unexpected").json()
        incident = body["error"]["detail"]["incident"]
        assert len(incident) == 12
        # A random token carries no information; the exception's text does.
        assert "hunter2" not in str(body)
        assert "RuntimeError" not in str(body)
        assert "Traceback" not in str(body)

    def test_the_incident_id_is_logged_with_the_traceback(self, api, caplog):
        with caplog.at_level("ERROR", logger="apps.core.exceptions"):
            body = api.get("/boom/unexpected").json()
        incident = body["error"]["detail"]["incident"]
        assert incident in caplog.text
        assert "hunter2" in caplog.text

    def test_each_incident_gets_its_own_id(self, api):
        first = api.get("/boom/unexpected").json()["error"]["detail"]["incident"]
        second = api.get("/boom/unexpected").json()["error"]["detail"]["incident"]
        assert first != second


class TestEnvelope:
    def test_an_unknown_code_still_gets_arabic(self):
        body = envelope("something_we_never_named")
        assert body["error"]["message"] == "تعذّر تنفيذ الطلب"
        assert body["error"]["detail"] == {}
