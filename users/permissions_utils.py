"""Effective page permissions for the current user."""

from __future__ import annotations

from typing import Any

from .models import Page, RolePermission, UserPermission


def normalize_page_url(url: str | None) -> str:
    if not url:
        return ""
    u = str(url).strip()
    if not u.startswith("/"):
        u = "/" + u
    if len(u) > 1 and u.endswith("/"):
        u = u.rstrip("/")
    return u


def build_permissions_payload(user) -> dict[str, Any]:
    """
    Merge RolePermission + UserPermission (user overrides role for same page).

    Fail-open when:
    - user.is_superuser
    - no Page rows exist yet (RBAC not configured)
    """
    role = getattr(user, "role", None)
    role_data = None
    if role is not None:
        role_data = {
            "id": role.id,
            "name": role.name,
            "name_ar": role.name_ar,
        }

    page_count = Page.objects.count()
    if getattr(user, "is_superuser", False) or page_count == 0:
        return {
            "user_id": user.id,
            "role": role_data,
            "unrestricted": True,
            "permissions": [],
        }

    by_page: dict[int, dict[str, Any]] = {}

    if role is not None:
        for rp in (
            RolePermission.objects.filter(role=role)
            .select_related("page")
            .order_by("page_id")
        ):
            page = rp.page
            by_page[page.id] = {
                "page_id": page.id,
                "name": page.name,
                "name_ar": page.name_ar,
                "url": normalize_page_url(page.url),
                "can_view": bool(rp.can_view),
                "can_add": bool(rp.can_add),
                "can_edit": bool(rp.can_edit),
                "can_delete": bool(rp.can_delete),
                "source": "role",
            }

    for up in (
        UserPermission.objects.filter(user=user)
        .select_related("page")
        .order_by("page_id")
    ):
        page = up.page
        by_page[page.id] = {
            "page_id": page.id,
            "name": page.name,
            "name_ar": page.name_ar,
            "url": normalize_page_url(page.url),
            "can_view": bool(up.can_view),
            "can_add": bool(up.can_add),
            "can_edit": bool(up.can_edit),
            "can_delete": bool(up.can_delete),
            "source": "user",
        }

    permissions = sorted(by_page.values(), key=lambda p: (p["url"], p["page_id"]))
    return {
        "user_id": user.id,
        "role": role_data,
        "unrestricted": False,
        "permissions": permissions,
    }


def user_can(user, page_url: str, action: str = "can_view") -> bool:
    """Check a single page action for API/UI enforcement."""
    if action not in {"can_view", "can_add", "can_edit", "can_delete"}:
        return False
    payload = build_permissions_payload(user)
    if payload.get("unrestricted"):
        return True
    target = normalize_page_url(page_url)
    for perm in payload.get("permissions") or []:
        url = normalize_page_url(perm.get("url"))
        if url == target and perm.get(action):
            return True
        # Parent grant: /admin can_view covers /admin/users
        if target.startswith(url + "/") and perm.get(action):
            return True
    return False
