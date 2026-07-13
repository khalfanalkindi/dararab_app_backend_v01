"""
Tests for page-RBAC API enforcement.

Run: python manage.py test users.tests_api_permissions
"""

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from users.api_permissions import (
    IsAuthenticatedWithPagePermission,
    iter_mapped_api_prefixes,
    normalize_request_path,
    resolve_action,
    resolve_page_urls,
)
from users.models import CustomUser, Page, Role, RolePermission


class PathMappingTests(SimpleTestCase):
    def test_write_routes_resolve_to_pages(self):
        samples = [
            "/api/sales/invoices/",
            "/api/sales/invoices/12/delete/",
            "/api/sales/invoices/5/generate-child/",
            "/api/sales/payments/",
            "/api/sales/customers/",
            "/api/inventory/transfers/bulk/",
            "/api/inventory/inventory/bulk/",
            "/api/inventory/inventory/bulk-delete/",
            "/api/inventory/products/3/delete/",
            "/api/inventory/projects/1/convert-to-product/",
            "/api/users/",
            "/api/roles/2/delete/",
            "/api/permissions/roles/",
            "/api/common/list-items/",
        ]
        for path in samples:
            pages = resolve_page_urls(path)
            self.assertIsNotNone(pages, f"unmapped write-capable path: {path}")
            self.assertTrue(len(pages) >= 1)

    def test_auth_login_unmapped_uses_exempt_list(self):
        self.assertIsNone(resolve_page_urls("/api/auth/login/"))

    def test_path_action_overrides(self):
        self.assertEqual(resolve_action("POST", "/api/inventory/inventory/bulk-delete/"), "can_delete")
        self.assertEqual(resolve_action("DELETE", "/api/sales/invoices/9/delete/"), "can_delete")
        self.assertEqual(
            resolve_action("POST", "/api/sales/product-sales-stats/1/recalculate/"),
            "can_edit",
        )
        self.assertEqual(
            resolve_action("POST", "/api/inventory/projects/1/convert-to-product/"),
            "can_edit",
        )
        self.assertEqual(resolve_action("POST", "/api/inventory/inventory/bulk/"), "can_edit")
        self.assertEqual(resolve_action("POST", "/api/inventory/transfers/bulk/"), "can_add")
        self.assertEqual(resolve_action("POST", "/api/sales/invoices/"), "can_add")
        self.assertEqual(resolve_action("PATCH", "/api/sales/invoices/1/"), "can_edit")

    def test_mapped_prefixes_cover_apps(self):
        prefixes = iter_mapped_api_prefixes()
        self.assertTrue(any(p.startswith("/api/sales/") for p in prefixes))
        self.assertTrue(any(p.startswith("/api/inventory/") for p in prefixes))
        self.assertTrue(any(p.startswith("/api/users") for p in prefixes))
        self.assertTrue(any(p.startswith("/api/common") for p in prefixes))


class PermissionEnforcementTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.perm = IsAuthenticatedWithPagePermission()

        self.page_invoices = Page.objects.create(
            name="Invoices", name_ar="فواتير", url="/invoices"
        )

        viewer_role = Role.objects.create(name="Viewer", name_ar="مشاهد")
        RolePermission.objects.create(
            role=viewer_role,
            page=self.page_invoices,
            can_view=True,
            can_add=False,
            can_edit=False,
            can_delete=False,
        )
        self.viewer = CustomUser.objects.create_user(
            username="viewer",
            password="test-pass-123",
            role=viewer_role,
        )

        writer_role = Role.objects.create(name="Writer", name_ar="كاتب")
        RolePermission.objects.create(
            role=writer_role,
            page=self.page_invoices,
            can_view=True,
            can_add=True,
            can_edit=True,
            can_delete=True,
        )
        self.writer = CustomUser.objects.create_user(
            username="writer",
            password="test-pass-123",
            role=writer_role,
        )

    def _check(self, user, method, path):
        request = getattr(self.factory, method.lower())(path)
        force_authenticate(request, user=user)
        return self.perm.has_permission(request, view=None)

    def test_viewer_cannot_post_invoice(self):
        with self.assertRaises(PermissionDenied) as ctx:
            self._check(self.viewer, "POST", "/api/sales/invoices/")
        detail = ctx.exception.detail
        self.assertEqual(detail["code"], "PERMISSION_DENIED")
        self.assertEqual(detail["action"], "can_add")

    def test_viewer_can_get_invoice(self):
        self.assertTrue(self._check(self.viewer, "GET", "/api/sales/invoices/"))

    def test_writer_can_post_invoice(self):
        self.assertTrue(self._check(self.writer, "POST", "/api/sales/invoices/"))

    def test_viewer_cannot_delete_invoice(self):
        with self.assertRaises(PermissionDenied):
            self._check(self.viewer, "DELETE", "/api/sales/invoices/1/delete/")

    def test_unmapped_write_denied(self):
        with self.assertRaises(PermissionDenied) as ctx:
            self._check(self.writer, "POST", "/api/unknown/thing/")
        self.assertEqual(ctx.exception.detail["code"], "UNMAPPED_ENDPOINT")

    def test_normalize_strips_trailing_slash(self):
        self.assertEqual(normalize_request_path("/api/sales/invoices/"), "/api/sales/invoices")
