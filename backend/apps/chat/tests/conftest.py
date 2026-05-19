import uuid

import pytest

from apps.chat.constants import (
    ConversationType,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    """Verified user override — chat tests require ``is_verified=True``."""
    return UserFactory(is_verified=True)


@pytest.fixture
def user_b(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_c(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def dm_conversation(db, user, user_b):
    """Create a DM conversation between user and user_b."""
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        scope_id=None,
        conversation_type=ConversationType.DIRECT,
        created_by_type=ParticipantType.USER,
        created_by_id=user.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    return conv


@pytest.fixture
def group_conversation(db, user, user_b, user_c):
    """Create a group conversation with user as admin."""
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        scope_id=None,
        conversation_type=ConversationType.GROUP,
        name="Test Group",
        created_by_type=ParticipantType.USER,
        created_by_id=user.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user.id,
        role=ParticipantRole.ADMIN,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_c.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    return conv


@pytest.fixture
def dm_with_request(db, user, user_b):
    """Create a DM where user_b has a pending chat request from user."""
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        scope_id=None,
        conversation_type=ConversationType.DIRECT,
        created_by_type=ParticipantType.USER,
        created_by_id=user.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.PENDING,
    )
    return conv


@pytest.fixture
def business(db):
    """Create a business with profile for testing."""
    from apps.core.constants import BusinessStatus
    from apps.organization.tests.factories import (
        BusinessAccountFactory,
        BusinessProfileFactory,
    )
    from apps.rbac.services import RBACService

    biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
    BusinessProfileFactory(business=biz, is_public=True)
    RBACService.initialize_business_account(business_id=biz.id, owner=biz.created_by)
    return biz


@pytest.fixture
def immediate_on_commit(monkeypatch):
    """Execute transaction.on_commit() callbacks immediately."""
    monkeypatch.setattr(
        "django.db.transaction.on_commit",
        lambda func, using=None, robust=False: func(),
    )
