"""
Chat Attachment Tests
=====================
Tests for image attachment upload, linking, and cleanup (Phase 4).
"""

import io
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.constants import (
    CHAT_MAX_ATTACHMENTS_PER_MESSAGE,
    CHAT_MAX_IMAGE_SIZE,
    AttachmentType,
    ConversationType,
    MessageContentType,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)
from apps.chat.services import ChatService
from apps.chat.tasks import cleanup_orphan_attachments
from apps.users.tests.factories import UserFactory


def _make_image_file(name="test.jpg", mime_type="image/jpeg", size=1024, ext="jpg"):
    """Create a fake image file for upload testing."""
    # Minimal valid JPEG (smallest valid JPEG header)
    content = b"\xff\xd8\xff\xe0" + b"\x00" * (size - 4)
    return SimpleUploadedFile(name, content, content_type=mime_type)


def _make_real_image(name="test.png", width=100, height=80):
    """Create a real PNG image for dimension extraction testing."""
    try:
        from PIL import Image

        img = Image.new("RGB", (width, height), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="image/png")
    except ImportError:
        pytest.skip("Pillow not installed")


# =============================================================================
# UPLOAD TESTS (SERVICE LEVEL)
# =============================================================================


@pytest.mark.django_db
class TestUploadAttachment:
    def test_upload_image_jpeg(self, dm_conversation, user):
        file = _make_image_file("photo.jpg", "image/jpeg")
        with patch(
            "django.core.files.storage.default_storage.save",
            return_value="chat/fake/key.jpg",
        ):
            att = ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )
        assert att.file_type == AttachmentType.IMAGE
        assert att.mime_type == "image/jpeg"
        assert att.original_filename == "photo.jpg"
        assert att.message is None  # orphan

    def test_upload_image_png(self, dm_conversation, user):
        file = _make_image_file("photo.png", "image/png", ext="png")
        with patch(
            "django.core.files.storage.default_storage.save",
            return_value="chat/fake/key.png",
        ):
            att = ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )
        assert att.mime_type == "image/png"

    def test_upload_image_gif(self, dm_conversation, user):
        file = _make_image_file("anim.gif", "image/gif", ext="gif")
        with patch(
            "django.core.files.storage.default_storage.save", return_value="key.gif"
        ):
            att = ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )
        assert att.mime_type == "image/gif"

    def test_upload_image_webp(self, dm_conversation, user):
        file = _make_image_file("pic.webp", "image/webp", ext="webp")
        with patch(
            "django.core.files.storage.default_storage.save", return_value="key.webp"
        ):
            att = ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )
        assert att.mime_type == "image/webp"

    def test_upload_rejects_non_image_mime(self, dm_conversation, user):
        file = _make_image_file("doc.pdf", "application/pdf", ext="pdf")
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )

    def test_upload_rejects_invalid_extension(self, dm_conversation, user):
        file = _make_image_file("script.exe", "image/jpeg", ext="exe")
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )

    def test_upload_rejects_oversized_file(self, dm_conversation, user):
        file = _make_image_file("big.jpg", "image/jpeg", size=CHAT_MAX_IMAGE_SIZE + 1)
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )

    def test_upload_requires_participant(self, dm_conversation):
        outsider = UserFactory(is_verified=True)
        file = _make_image_file()
        from apps.core.exceptions import PermissionDenied

        with pytest.raises(PermissionDenied):
            ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=outsider,
                file=file,
            )

    def test_upload_extracts_dimensions(self, dm_conversation, user):
        file = _make_real_image("pic.png", width=200, height=150)
        with patch(
            "django.core.files.storage.default_storage.save", return_value="key.png"
        ):
            att = ChatService.upload_attachment(
                conversation_id=dm_conversation.id,
                user=user,
                file=file,
            )
        assert att.width == 200
        assert att.height == 150


# =============================================================================
# UPLOAD VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestAttachmentUploadView:
    def test_upload_via_api(self, authenticated_client, dm_conversation):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/upload/"
        file = _make_image_file()
        with patch(
            "django.core.files.storage.default_storage.save", return_value="key.jpg"
        ):
            with patch(
                "django.core.files.storage.default_storage.url",
                return_value="/media/key.jpg",
            ):
                resp = authenticated_client.post(
                    url, {"file": file}, format="multipart"
                )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "id" in resp.data
        assert resp.data["file_type"] == "image"

    def test_upload_requires_authentication(self, api_client, dm_conversation):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/upload/"
        file = _make_image_file()
        resp = api_client.post(url, {"file": file}, format="multipart")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_no_file_returns_400(self, authenticated_client, dm_conversation):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/upload/"
        resp = authenticated_client.post(url, {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# MESSAGE WITH ATTACHMENTS
# =============================================================================


@pytest.mark.django_db
class TestMessageWithAttachments:
    def _create_orphan(self, conversation, user):
        return MessageAttachment.objects.create(
            message=None,
            conversation=conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key=f"chat/test/{uuid.uuid4().hex}.jpg",
            original_filename="photo.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )

    def test_send_message_with_attachment_ids(self, dm_conversation, user):
        att = self._create_orphan(dm_conversation, user)
        message = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Check this out",
            attachment_ids=[att.id],
        )
        att.refresh_from_db()
        assert att.message_id == message.id

    def test_send_attachment_only_message(self, dm_conversation, user):
        att = self._create_orphan(dm_conversation, user)
        message = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="",
            attachment_ids=[att.id],
        )
        assert message is not None
        att.refresh_from_db()
        assert att.message_id == message.id

    def test_send_rejects_empty_content_no_attachments(self, dm_conversation, user):
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="",
            )

    def test_send_rejects_invalid_attachment_ids(self, dm_conversation, user):
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="Hello",
                attachment_ids=[uuid.uuid4()],
            )

    def test_send_rejects_others_attachments(self, dm_conversation, user, user_b):
        att = self._create_orphan(dm_conversation, user_b)
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="Hello",
                attachment_ids=[att.id],
            )

    def test_send_rejects_already_linked_attachments(self, dm_conversation, user):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="Old",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )
        att = MessageAttachment.objects.create(
            message=msg,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/linked.jpg",
            original_filename="linked.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="Hello",
                attachment_ids=[att.id],
            )

    def test_send_rejects_too_many_attachments(self, dm_conversation, user):
        atts = [
            self._create_orphan(dm_conversation, user)
            for _ in range(CHAT_MAX_ATTACHMENTS_PER_MESSAGE + 1)
        ]
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="Hello",
                attachment_ids=[a.id for a in atts],
            )


# =============================================================================
# MESSAGE OUTPUT INCLUDES ATTACHMENTS
# =============================================================================


@pytest.mark.django_db
class TestMessageOutputAttachments:
    def test_message_output_includes_attachments(
        self, authenticated_client, dm_conversation, user
    ):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="Look at this",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )
        MessageAttachment.objects.create(
            message=msg,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/output.jpg",
            original_filename="output.jpg",
            mime_type="image/jpeg",
            file_size=2048,
            width=800,
            height=600,
        )

        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        with patch(
            "django.core.files.storage.default_storage.url",
            return_value="/media/chat/test/output.jpg",
        ):
            resp = authenticated_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        msgs = resp.data
        assert len(msgs) == 1
        assert len(msgs[0]["attachments"]) == 1
        att_data = msgs[0]["attachments"][0]
        assert att_data["original_filename"] == "output.jpg"
        assert att_data["width"] == 800
        assert att_data["height"] == 600
        assert "url" in att_data

    def test_attachment_output_has_url(self, dm_conversation, user):
        att = MessageAttachment.objects.create(
            message=None,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/url.jpg",
            original_filename="url.jpg",
            mime_type="image/jpeg",
            file_size=512,
        )
        from apps.chat.serializers import AttachmentOutputSerializer

        with patch(
            "django.core.files.storage.default_storage.url",
            return_value="/media/chat/test/url.jpg",
        ):
            data = AttachmentOutputSerializer(att).data
        assert "/media/chat/test/url.jpg" in data["url"]


# =============================================================================
# WS SERIALIZER
# =============================================================================


@pytest.mark.django_db
class TestWSSerializeAttachment:
    def test_ws_serialize_message_includes_attachments(self, dm_conversation, user):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="ws test",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )
        MessageAttachment.objects.create(
            message=msg,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/ws.jpg",
            original_filename="ws.jpg",
            mime_type="image/jpeg",
            file_size=512,
        )

        from apps.chat.ws_serializers import serialize_message

        with patch(
            "django.core.files.storage.default_storage.url",
            return_value="/media/ws.jpg",
        ):
            payload = serialize_message(msg)

        assert "attachments" in payload
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["original_filename"] == "ws.jpg"


# =============================================================================
# ORPHAN CLEANUP TASK
# =============================================================================


@pytest.mark.django_db
class TestCleanupOrphanAttachments:
    def test_cleanup_deletes_old_orphans(self, dm_conversation, user):
        att = MessageAttachment.objects.create(
            message=None,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/orphan.jpg",
            original_filename="orphan.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )
        # Make it old
        cutoff = timezone.now() - timedelta(hours=25)
        MessageAttachment.objects.filter(id=att.id).update(created_at=cutoff)

        with patch("django.core.files.storage.default_storage.delete"):
            count = cleanup_orphan_attachments()

        assert count == 1
        assert not MessageAttachment.objects.filter(id=att.id).exists()

    def test_cleanup_skips_linked_attachments(self, dm_conversation, user):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="linked",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )
        att = MessageAttachment.objects.create(
            message=msg,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/linked.jpg",
            original_filename="linked.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )
        cutoff = timezone.now() - timedelta(hours=25)
        MessageAttachment.objects.filter(id=att.id).update(created_at=cutoff)

        count = cleanup_orphan_attachments()

        assert count == 0
        assert MessageAttachment.objects.filter(id=att.id).exists()

    def test_cleanup_skips_recent_orphans(self, dm_conversation, user):
        att = MessageAttachment.objects.create(
            message=None,
            conversation=dm_conversation,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key="chat/test/recent.jpg",
            original_filename="recent.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )

        count = cleanup_orphan_attachments()

        assert count == 0
        assert MessageAttachment.objects.filter(id=att.id).exists()
