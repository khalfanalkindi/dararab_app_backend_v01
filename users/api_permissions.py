"""
DRF permission: authenticated + page RBAC (can_view / can_add / can_edit / can_delete).

Maps API path prefixes → frontend Page.url values (Admin → Pages).
Shared APIs (e.g. invoices used by POS + Invoices) allow access if the user
has the required action on ANY mapped page.

Security posture:
- Exempt auth/self endpoints only.
- Superuser / empty Page table → unrestricted (bootstrap).
- Unmapped API paths are DENIED for everyone else (no fail-open).
- Destructive path suffixes (…/delete/, bulk-delete, recalculate) map to
  can_delete / can_edit even when the HTTP verb is POST.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .permissions_utils import build_permissions_payload, user_can

logger = logging.getLogger(__name__)

# Auth / self endpoints — must not require a Page row
EXEMPT_PREFIXES = (
    "/api/auth/login",
    "/api/auth/token/refresh",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/auth/my-permissions",
    "/api/auth/me",
    "/api/auth/change-password",
)

# Longest-prefix match: (api_prefix, page_url | list[page_url])
_API_PAGE_RULES: list[tuple[str, tuple[str, ...]]] = [
    # Sales
    ("/api/sales/customers", ("/definitions/customers",)),
    ("/api/sales/invoices/outstanding-payments", ("/outstanding-payment",)),
    ("/api/sales/invoices/partial-payments", ("/outstanding-payment",)),
    ("/api/sales/invoices/debug", ("/invoices", "/pos", "/outstanding-payment")),
    ("/api/sales/invoices", ("/invoices", "/pos", "/outstanding-payment")),
    ("/api/sales/invoice-items", ("/invoices", "/pos", "/outstanding-payment")),
    ("/api/sales/payments", ("/pos", "/outstanding-payment", "/invoices")),
    ("/api/sales/returns", ("/invoices", "/pos")),
    ("/api/sales/dashboard", ("/dashboard",)),
    ("/api/sales/warehouse-dashboard", ("/reports/warehouse-stat", "/dashboard")),
    ("/api/sales/product-sales-stats", ("/reports/warehouse-stat", "/dashboard")),
    ("/api/sales/products", ("/reports/book-sales", "/reports/warehouse-stat", "/dashboard")),
    ("/api/sales/calculate-royalties", ("/reports/royalties",)),
    # Inventory / catalog
    ("/api/inventory/pos-product-summary", ("/pos",)),
    ("/api/inventory/product-summary", ("/products", "/inventory", "/transfer", "/pos")),
    ("/api/inventory/projects", ("/projects",)),
    ("/api/inventory/contracts", ("/projects-contracts",)),
    ("/api/inventory/products", ("/products", "/pos", "/inventory", "/transfer")),
    ("/api/inventory/print-runs", ("/products",)),
    ("/api/inventory/print-tasks", ("/products",)),
    ("/api/inventory/warehouses", ("/definitions/warehouses", "/inventory", "/pos", "/transfer")),
    ("/api/inventory/stock-writeoffs", ("/inventory/writeoffs", "/inventory")),
    ("/api/inventory/inventory", ("/inventory", "/pos", "/transfer", "/invoices")),
    ("/api/inventory/transfer-preview", ("/transfer",)),
    ("/api/inventory/transfers", ("/transfer",)),
    ("/api/inventory/authors", ("/definitions/authors", "/projects", "/products")),
    ("/api/inventory/translators", ("/definitions/translators", "/projects", "/products")),
    ("/api/inventory/rights-owners", ("/definitions/rights_owner", "/projects", "/products")),
    ("/api/inventory/reviewers", ("/projects", "/products")),
    ("/api/inventory/stakeholders", ("/projects",)),
    ("/api/inventory/bootstrap", ("/products", "/inventory", "/projects")),
    # Admin / users
    ("/api/users", ("/admin/users",)),
    ("/api/roles", ("/admin/roles",)),
    ("/api/pages", ("/admin/pages",)),
    ("/api/permissions/roles", ("/admin/role-permissions",)),
    ("/api/permissions/users", ("/admin/user-permissions",)),
    # Common definitions
    ("/api/common", ("/admin/common",)),
]

# Path suffix → required action (checked before HTTP-method mapping)
_PATH_ACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"/bulk-delete/?$"), "can_delete"),
    (re.compile(r"/delete/?$"), "can_delete"),
    (re.compile(r"/recalculate(?:-all)?/?$"), "can_edit"),
    (re.compile(r"/convert-to-product/?$"), "can_edit"),
    # Upserts mutate existing rows — require edit (not only add)
    (re.compile(r"/inventory/inventory/bulk/?$"), "can_edit"),
    (re.compile(r"/inventory/print-runs/bulk/?$"), "can_edit"),
]


def _sorted_rules() -> list[tuple[str, tuple[str, ...]]]:
    return sorted(_API_PAGE_RULES, key=lambda r: len(r[0]), reverse=True)


def normalize_request_path(path: str) -> str:
    p = (path or "").split("?")[0]
    if not p.startswith("/"):
        p = "/" + p
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def resolve_page_urls(request_path: str) -> tuple[str, ...] | None:
    """Return mapped page URLs for an API path, or None if unmapped."""
    path = normalize_request_path(request_path)
    for prefix, pages in _sorted_rules():
        pref = prefix.rstrip("/")
        if path == pref or path.startswith(pref + "/"):
            return pages
    return None


def method_to_action(method: str) -> str:
    m = (method or "GET").upper()
    if m in SAFE_METHODS or m == "OPTIONS":
        return "can_view"
    if m == "POST":
        return "can_add"
    if m in {"PUT", "PATCH"}:
        return "can_edit"
    if m == "DELETE":
        return "can_delete"
    return "can_view"


def resolve_action(method: str, request_path: str) -> str:
    """HTTP method + path-suffix overrides → RBAC action."""
    path = normalize_request_path(request_path)
    for pattern, action in _PATH_ACTION_RULES:
        if pattern.search(path):
            return action
    return method_to_action(method)


def user_can_any(user, page_urls: Iterable[str], action: str) -> bool:
    payload = build_permissions_payload(user)
    if payload.get("unrestricted"):
        return True
    for url in page_urls:
        if user_can(user, url, action):
            return True
    return False


def is_exempt_path(path: str) -> bool:
    p = normalize_request_path(path)
    for prefix in EXEMPT_PREFIXES:
        if p == prefix or p.startswith(prefix + "/"):
            return True
    return False


def is_write_method(method: str) -> bool:
    return (method or "GET").upper() not in SAFE_METHODS and (method or "").upper() != "OPTIONS"


def iter_mapped_api_prefixes() -> list[str]:
    """Prefixes covered by RBAC (for audits / tests)."""
    return [prefix for prefix, _ in _API_PAGE_RULES]


class IsAuthenticatedWithPagePermission(BasePermission):
    """
    1) User must be authenticated
    2) Exempt auth paths → allow
    3) Unrestricted (superuser / no Page rows) → allow
    4) Unmapped API path → DENY (structured 403)
    5) Else require mapped page action for the HTTP verb / path suffix
    """

    message = "You do not have permission to perform this action on this page."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        path = normalize_request_path(getattr(request, "path", "") or "")
        if is_exempt_path(path):
            return True

        # Superuser / unconfigured Pages: unrestricted
        payload = build_permissions_payload(user)
        if payload.get("unrestricted"):
            return True

        action = resolve_action(request.method, path)
        pages = resolve_page_urls(path)

        if pages is None:
            logger.warning(
                "RBAC deny unmapped path user=%s path=%s method=%s",
                getattr(user, "id", None),
                path,
                request.method,
            )
            raise PermissionDenied(
                detail={
                    "code": "UNMAPPED_ENDPOINT",
                    "detail": "This API path is not registered for page permissions.",
                    "path": path,
                    "action": action,
                }
            )

        allowed = user_can_any(user, pages, action)
        if not allowed:
            logger.info(
                "RBAC deny user=%s path=%s action=%s pages=%s",
                getattr(user, "id", None),
                path,
                action,
                pages,
            )
            raise PermissionDenied(
                detail={
                    "code": "PERMISSION_DENIED",
                    "detail": (
                        f"Missing {action} permission for this resource. "
                        f"Required page access: {', '.join(pages)}"
                    ),
                    "action": action,
                    "pages": list(pages),
                    "path": path,
                }
            )
        return True


# Drop-in alias so existing `permission_classes = [IsAuthenticated]` keeps working
# when views import from this module.
IsAuthenticated = IsAuthenticatedWithPagePermission
