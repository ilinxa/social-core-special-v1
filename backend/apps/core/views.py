# apps/core/views.py
"""
Core Views - Shared view mixins for the platform.

Provides reusable view mixins that can be composed with DRF APIView.

Mixins:
    PermissionInjectMixin - Injects _permissions into GET detail responses.
    RelationshipInjectMixin - Injects _relationship into GET detail responses
                              for authenticated users.
"""


class RelationshipInjectMixin:
    """
    Inject _relationship into GET detail responses for authenticated users.

    Shows the requesting user's relationship with the resource:
    - membership_status: current membership status (or null)
    - active_transaction: any active transaction in the relevant
      conflict group (or null)

    Views must:
      1. Implement `_build_relationship_data()` returning a dict
      2. Set `self._inject_relationship = True` in get() to opt in

    MRO: Place before PermissionInjectMixin so both finalize_response()
    calls chain correctly via super().
    """

    _inject_relationship = False

    def _build_relationship_data(self) -> dict | None:
        """Override to compute relationship data for the authenticated user."""
        raise NotImplementedError

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if (
            self._inject_relationship
            and request.method == "GET"
            and hasattr(request, "user")
            and request.user
            and request.user.is_authenticated
            and hasattr(response, "data")
            and isinstance(response.data, dict)
        ):
            relationship = self._build_relationship_data()
            if relationship is not None:
                response.data["_relationship"] = relationship

        return response


class PermissionInjectMixin:
    """
    Inject _permissions into GET detail responses.

    Adds a `_permissions` dict to successful GET responses containing
    evaluated booleans from the view's policy class. This allows the
    frontend to know what the requesting user can do on the resource
    without extra API calls.

    Views must:
      1. Set `policy_class = SomePolicy`
      2. Implement `_build_policy_kwargs()` returning kwargs for
         `policy_class.get_viewer_permissions(**kwargs)`
      3. Set `self._inject_permissions = True` in get() to opt in

    The opt-in flag prevents accidental injection into paginated list
    responses, error responses, or redirect responses.
    """

    policy_class = None
    _inject_permissions = False

    def _build_policy_kwargs(self) -> dict:
        """Override to pass correct kwargs to policy.get_viewer_permissions()."""
        raise NotImplementedError

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if (
            self._inject_permissions
            and request.method == "GET"
            and self.policy_class is not None
            and hasattr(response, "data")
            and isinstance(response.data, dict)
        ):
            response.data["_permissions"] = self.policy_class.get_viewer_permissions(
                **self._build_policy_kwargs()
            )

        return response
