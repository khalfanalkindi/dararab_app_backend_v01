"""
Standard API error shape for all DRF exceptions:

  {
    "detail": "Human-readable summary",
    "code": "VALIDATION_ERROR",
    "field_errors": { "email": ["This field is required."] },
    ...optional domain extras (pages, product_ids, etc.)
  }

Wire via REST_FRAMEWORK['EXCEPTION_HANDLER'].
Use error_response() for manual error Responses in views.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

# Keys that are domain metadata, not serializer field errors.
_DOMAIN_EXTRA_KEYS = frozenset(
    {
        "pages",
        "path",
        "action",
        "product_ids",
        "errors",
        "succeeded",
        "failed",
        "success_count",
        "failed_count",
        "total_requested",
        "mode",
        "index",
        "id",
        "transfer_id",
        "quantity",
    }
)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                out.append(str(item.get("detail") or item.get("message") or item))
            else:
                out.append(str(item))
        return out
    if isinstance(value, dict):
        # Nested serializer errors → flatten to readable strings
        parts: list[str] = []
        for k, v in value.items():
            nested = _as_str_list(v)
            for msg in nested:
                parts.append(f"{k}: {msg}" if k != "non_field_errors" else msg)
        return parts or [str(value)]
    return [str(value)]


def _stringify_detail(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        parts = [str(x) for x in value if x is not None and str(x)]
        return "; ".join(parts) if parts else None
    if isinstance(value, dict):
        # Unexpected nested detail — take first message-like value
        for k in ("detail", "message", "error"):
            if k in value:
                return _stringify_detail(value[k])
        return str(value)
    return str(value)


def _first_field_message(field_errors: Mapping[str, list[str]]) -> Optional[str]:
    for field, messages in field_errors.items():
        if not messages:
            continue
        if field == "non_field_errors":
            return messages[0]
        return f"{field}: {messages[0]}"
    return None


def _looks_like_field_error(value: Any) -> bool:
    """Heuristic: DRF validation values are message strings, lists, or nested dicts."""
    if isinstance(value, str):
        return True
    if isinstance(value, dict):
        return True
    if isinstance(value, (list, tuple)):
        return True
    return False


def default_code_for_exception(exc: Exception, status_code: int) -> str:
    if isinstance(exc, NotAuthenticated):
        return "NOT_AUTHENTICATED"
    if isinstance(exc, AuthenticationFailed):
        return "AUTHENTICATION_FAILED"
    if isinstance(exc, PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, NotFound):
        return "NOT_FOUND"
    if isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, APIException):
        # Use DRF's default_code when available (e.g. method_not_allowed)
        code = getattr(exc, "default_code", None) or getattr(exc, "code", None)
        if code:
            return str(code).upper()
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "THROTTLED"
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "BAD_REQUEST"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "UNAUTHORIZED"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "FORBIDDEN"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "NOT_FOUND"
    if status_code >= 500:
        return "SERVER_ERROR"
    return f"HTTP_{status_code}"


def normalize_error_payload(
    data: Any,
    *,
    default_code: str = "ERROR",
    default_detail: str = "Request failed.",
) -> dict[str, Any]:
    """
    Normalize arbitrary DRF / view error bodies into the standard shape.
    Preserves known domain extras at the top level.
    """
    field_errors: dict[str, list[str]] = {}
    extras: dict[str, Any] = {}
    code: Optional[str] = None
    detail: Optional[str] = None

    if isinstance(data, dict):
        raw_code = data.get("code")
        if raw_code is not None and raw_code != "":
            code = str(raw_code)

        detail = _stringify_detail(data.get("detail"))
        # Legacy / alternate keys
        if not detail:
            detail = _stringify_detail(data.get("message")) or _stringify_detail(data.get("error"))

        fe = data.get("field_errors")
        if isinstance(fe, dict):
            for k, v in fe.items():
                field_errors[str(k)] = _as_str_list(v)

        for key, value in data.items():
            if key in ("code", "detail", "field_errors", "message", "error"):
                continue
            if key in _DOMAIN_EXTRA_KEYS:
                extras[key] = value
                continue
            if key == "non_field_errors":
                field_errors["non_field_errors"] = _as_str_list(value)
                continue
            if _looks_like_field_error(value):
                field_errors[str(key)] = _as_str_list(value)
            else:
                extras[key] = value

    elif isinstance(data, (list, tuple)):
        field_errors["non_field_errors"] = _as_str_list(data)
        detail = "; ".join(field_errors["non_field_errors"]) or None
    elif data is not None:
        detail = str(data)

    if not detail:
        detail = _first_field_message(field_errors) or default_detail

    payload: dict[str, Any] = {
        "detail": detail,
        "code": code or default_code,
        "field_errors": field_errors,
    }
    payload.update(extras)
    return payload


def error_response(
    *,
    code: str,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    field_errors: Optional[Mapping[str, Any]] = None,
    **extras: Any,
) -> Response:
    """Build a Response already in the standard error shape."""
    fe: dict[str, list[str]] = {}
    if field_errors:
        for k, v in field_errors.items():
            fe[str(k)] = _as_str_list(v)
    body: MutableMapping[str, Any] = {
        "detail": detail,
        "code": code,
        "field_errors": fe,
    }
    body.update(extras)
    return Response(body, status=status_code)


def custom_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER — always returns {detail, code, field_errors} (+ extras)."""
    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    default_code = default_code_for_exception(exc, response.status_code)
    default_detail = "Request failed."
    if isinstance(exc, APIException):
        # Prefer exception's string form when detail was a plain string
        try:
            if isinstance(exc.detail, str):
                default_detail = exc.detail
            elif isinstance(exc.detail, list) and exc.detail:
                default_detail = "; ".join(str(x) for x in exc.detail)
        except Exception:
            pass

    response.data = normalize_error_payload(
        response.data,
        default_code=default_code,
        default_detail=default_detail,
    )
    return response
