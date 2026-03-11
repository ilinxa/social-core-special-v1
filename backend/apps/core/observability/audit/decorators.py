"""
Audit Decorators
================
Decorators for automatic audit logging of function calls.

Usage:
    from apps.core.observability.audit import audited, AuditLog

    @audited(
        action=AuditLog.Action.USER_UPDATED,
        resource_param='user',
        actor_param='updated_by',
    )
    def update_user(*, user: User, updated_by: User, data: dict) -> User:
        ...
"""

import functools
from typing import Any, Callable, Optional

from apps.core.observability.audit.models import AuditLog
from apps.core.observability.audit.service import AuditService


def audited(
    action: str,
    *,
    resource_param: Optional[str] = None,
    actor_param: str = "actor",
    request_param: str = "request",
    include_result: bool = False,
):
    """
    Decorator to automatically audit function calls.

    Logs the action on success or failure, extracting actor, resource,
    and request from function parameters.

    Args:
        action: Action type to log (from AuditLog.Action)
        resource_param: Parameter name containing the resource
        actor_param: Parameter name containing the actor
        request_param: Parameter name containing the request
        include_result: If True, include function result in details

    Usage:
        @audited(
            action=AuditLog.Action.USER_UPDATED,
            resource_param='user',
            actor_param='updated_by',
        )
        def update_user(*, user: User, updated_by: User, data: dict) -> User:
            ...

        @audited(
            action=AuditLog.Action.SESSION_CREATED,
            actor_param='user',
            include_result=True,
        )
        def create_session(*, user: User, device_info: dict) -> Session:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Extract parameters
            actor = kwargs.get(actor_param)
            resource = kwargs.get(resource_param) if resource_param else None
            request = kwargs.get(request_param)

            try:
                result = func(*args, **kwargs)

                # Log success
                details = {}
                if include_result and result:
                    details["result_id"] = str(getattr(result, "id", result))

                AuditService.log(
                    action=action,
                    actor=actor,
                    resource=resource or result,
                    request=request,
                    outcome=AuditLog.Outcome.SUCCESS,
                    details=details,
                )

                return result

            except Exception as e:
                # Log failure
                AuditService.log(
                    action=action,
                    actor=actor,
                    resource=resource,
                    request=request,
                    outcome=AuditLog.Outcome.FAILURE,
                    details={"error": str(e), "error_type": type(e).__name__},
                )
                raise

        return wrapper

    return decorator
