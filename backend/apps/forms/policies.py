from apps.core.exceptions import PermissionDenied
from apps.core.types import ActorContext
from apps.forms.models import FormResponse, FormTemplate


class FormTemplatePolicy:
    """Authorization policies for form templates."""

    @staticmethod
    def can_create_form(*, actor_context: ActorContext, owner_type: str) -> None:
        if not actor_context.has_permission("can_create_form"):
            raise PermissionDenied(
                message="You do not have permission to create forms",
                action="create",
                resource="FormTemplate",
            )

    @staticmethod
    def can_edit_form(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be edited",
                action="edit",
                resource="FormTemplate",
            )
        if not actor_context.has_permission("can_edit_form"):
            raise PermissionDenied(
                message="You do not have permission to edit forms",
                action="edit",
                resource="FormTemplate",
            )

    @staticmethod
    def can_delete_form(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be deleted",
                action="delete",
                resource="FormTemplate",
            )
        if not actor_context.has_permission("can_delete_form"):
            raise PermissionDenied(
                message="You do not have permission to delete forms",
                action="delete",
                resource="FormTemplate",
            )

    @staticmethod
    def can_publish_form(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be published via API",
                action="publish",
                resource="FormTemplate",
            )
        if not actor_context.has_permission("can_edit_form"):
            raise PermissionDenied(
                message="You do not have permission to publish forms",
                action="publish",
                resource="FormTemplate",
            )

    @staticmethod
    def can_archive_form(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be archived",
                action="archive",
                resource="FormTemplate",
            )
        if not actor_context.has_permission("can_edit_form"):
            raise PermissionDenied(
                message="You do not have permission to archive forms",
                action="archive",
                resource="FormTemplate",
            )

    @staticmethod
    def can_view_responses(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if not actor_context.has_permission("can_view_responses"):
            raise PermissionDenied(
                message="You do not have permission to view responses",
                action="view",
                resource="FormResponse",
            )

    @staticmethod
    def can_fork_template(*, actor_context: ActorContext) -> None:
        if not actor_context.has_permission("can_create_form"):
            raise PermissionDenied(
                message="You do not have permission to fork templates",
                action="fork",
                resource="FormTemplate",
            )

    @staticmethod
    def get_viewer_permissions(
        *, actor_context: ActorContext, form_template: FormTemplate
    ) -> dict:
        """
        Get evaluated permissions for the requesting user on this form template.

        Returns a dict of boolean permission flags for frontend UI gating.
        Uses _safe_check to convert exception-raising policy methods to booleans.
        """

        def _safe_check(fn, **kwargs) -> bool:
            try:
                fn(**kwargs)
                return True
            except PermissionDenied:
                return False

        return {
            "can_edit": _safe_check(
                FormTemplatePolicy.can_edit_form,
                actor_context=actor_context,
                form_template=form_template,
            ),
            "can_delete": _safe_check(
                FormTemplatePolicy.can_delete_form,
                actor_context=actor_context,
                form_template=form_template,
            ),
            "can_publish": _safe_check(
                FormTemplatePolicy.can_publish_form,
                actor_context=actor_context,
                form_template=form_template,
            ),
            "can_archive": _safe_check(
                FormTemplatePolicy.can_archive_form,
                actor_context=actor_context,
                form_template=form_template,
            ),
        }


class FormResponsePolicy:
    """Authorization policies for form responses."""

    @staticmethod
    def can_view_own_response(*, user, response: FormResponse) -> None:
        if response.submitted_by_id != user.id:
            raise PermissionDenied(
                message="You can only view your own responses",
                action="view",
                resource="FormResponse",
            )

    @staticmethod
    def can_edit_response(*, user, response: FormResponse) -> None:
        if response.submitted_by_id != user.id:
            raise PermissionDenied(
                message="You can only edit your own responses",
                action="edit",
                resource="FormResponse",
            )
        if not response.is_editable:
            raise PermissionDenied(
                message="This response cannot be edited",
                action="edit",
                resource="FormResponse",
            )

    @staticmethod
    def can_process_response(
        *,
        actor_context: ActorContext,
        response: FormResponse,
    ) -> None:
        if not actor_context.has_permission("can_process_response"):
            raise PermissionDenied(
                message="You do not have permission to process responses",
                action="process",
                resource="FormResponse",
            )

    @staticmethod
    def can_export_responses(
        *,
        actor_context: ActorContext,
        form_template: FormTemplate,
    ) -> None:
        if not actor_context.has_permission("can_export_responses"):
            raise PermissionDenied(
                message="You do not have permission to export responses",
                action="export",
                resource="FormResponse",
            )

    @staticmethod
    def get_viewer_permissions(
        *,
        user,
        response: FormResponse,
        actor_context: ActorContext | None = None,
    ) -> dict:
        """Boolean permission flags for the requesting user on this response.

        Mirrors ``FormTemplatePolicy.get_viewer_permissions`` shape. The
        ``actor_context`` is optional because some checks (own-response view
        and edit) only need the User; process and export need full RBAC
        context, which the view supplies when the user is a member of the
        form's owner account.
        """

        def _safe_check(fn, **kwargs) -> bool:
            try:
                fn(**kwargs)
                return True
            except PermissionDenied:
                return False

        perms: dict = {
            "can_view": _safe_check(
                FormResponsePolicy.can_view_own_response,
                user=user,
                response=response,
            ),
            "can_edit": _safe_check(
                FormResponsePolicy.can_edit_response,
                user=user,
                response=response,
            ),
        }
        if actor_context is not None:
            perms["can_process"] = _safe_check(
                FormResponsePolicy.can_process_response,
                actor_context=actor_context,
                response=response,
            )
            perms["can_export"] = _safe_check(
                FormResponsePolicy.can_export_responses,
                actor_context=actor_context,
                form_template=response.form_template,
            )
        else:
            perms["can_process"] = False
            perms["can_export"] = False
        return perms
