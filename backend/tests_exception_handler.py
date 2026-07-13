"""Unit tests for standard API error payload normalization (no DB)."""

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from backend.exception_handler import (
    default_code_for_exception,
    error_response,
    normalize_error_payload,
)


class NormalizeErrorPayloadTests(SimpleTestCase):
    def test_validation_dict_becomes_field_errors(self):
        payload = normalize_error_payload(
            {"email": ["This field is required."], "name": ["Too short."]},
            default_code="VALIDATION_ERROR",
        )
        self.assertEqual(payload["code"], "VALIDATION_ERROR")
        self.assertIn("email", payload["field_errors"])
        self.assertEqual(payload["field_errors"]["email"], ["This field is required."])
        self.assertTrue(payload["detail"])  # summary from first field

    def test_preserves_structured_permission_denied(self):
        payload = normalize_error_payload(
            {
                "code": "PERMISSION_DENIED",
                "detail": "Missing can_edit permission for this resource.",
                "action": "can_edit",
                "pages": ["/pos"],
                "path": "/api/sales/invoices/",
            },
            default_code="FORBIDDEN",
        )
        self.assertEqual(payload["code"], "PERMISSION_DENIED")
        self.assertEqual(payload["detail"], "Missing can_edit permission for this resource.")
        self.assertEqual(payload["field_errors"], {})
        self.assertEqual(payload["pages"], ["/pos"])
        self.assertEqual(payload["action"], "can_edit")

    def test_plain_detail_string(self):
        payload = normalize_error_payload(
            {"detail": "Not found."},
            default_code="NOT_FOUND",
        )
        self.assertEqual(payload["detail"], "Not found.")
        self.assertEqual(payload["code"], "NOT_FOUND")
        self.assertEqual(payload["field_errors"], {})

    def test_non_field_errors(self):
        payload = normalize_error_payload(
            {"non_field_errors": ["Invalid combination."]},
            default_code="VALIDATION_ERROR",
        )
        self.assertEqual(payload["field_errors"]["non_field_errors"], ["Invalid combination."])
        self.assertEqual(payload["detail"], "Invalid combination.")

    def test_invoice_delete_extras_preserved(self):
        payload = normalize_error_payload(
            {
                "code": "INVENTORY_CONFLICT",
                "detail": "Could not restore inventory.",
                "product_ids": [1, 2],
                "errors": [{"product_id": 1, "detail": "lock"}],
            },
            default_code="BAD_REQUEST",
        )
        self.assertEqual(payload["code"], "INVENTORY_CONFLICT")
        self.assertEqual(payload["product_ids"], [1, 2])
        self.assertEqual(payload["field_errors"], {})
        self.assertTrue(payload["errors"])


class DefaultCodeTests(SimpleTestCase):
    def test_exception_mapping(self):
        self.assertEqual(
            default_code_for_exception(NotAuthenticated(), 401),
            "NOT_AUTHENTICATED",
        )
        self.assertEqual(
            default_code_for_exception(AuthenticationFailed(), 401),
            "AUTHENTICATION_FAILED",
        )
        self.assertEqual(
            default_code_for_exception(PermissionDenied(), 403),
            "PERMISSION_DENIED",
        )
        self.assertEqual(
            default_code_for_exception(NotFound(), 404),
            "NOT_FOUND",
        )
        self.assertEqual(
            default_code_for_exception(ValidationError("bad"), 400),
            "VALIDATION_ERROR",
        )


class ErrorResponseHelperTests(SimpleTestCase):
    def test_error_response_shape(self):
        res = error_response(
            code="MISSING_WAREHOUSE",
            detail="No warehouse on invoice.",
            status_code=status.HTTP_400_BAD_REQUEST,
            product_ids=[9],
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "MISSING_WAREHOUSE")
        self.assertEqual(res.data["detail"], "No warehouse on invoice.")
        self.assertEqual(res.data["field_errors"], {})
        self.assertEqual(res.data["product_ids"], [9])
