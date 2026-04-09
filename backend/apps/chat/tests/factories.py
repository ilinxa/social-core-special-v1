import factory
from factory.django import DjangoModelFactory

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import ChatBlock, Conversation, ConversationParticipant, Message
from apps.users.tests.factories import UserFactory


class ConversationFactory(DjangoModelFactory):
    class Meta:
        model = Conversation

    scope_type = ScopeType.GLOBAL
    scope_id = None
    conversation_type = ConversationType.DIRECT
    name = ""
    created_by_type = ParticipantType.USER
    created_by_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    is_active = True


class ConversationParticipantFactory(DjangoModelFactory):
    class Meta:
        model = ConversationParticipant

    conversation = factory.SubFactory(ConversationFactory)
    participant_type = ParticipantType.USER
    participant_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    role = ParticipantRole.MEMBER
    request_status = RequestStatus.NONE
    is_active = True


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    sender_type = ParticipantType.USER
    sender_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
    content_type = MessageContentType.TEXT
    content = factory.Faker("sentence")
    sequence_number = factory.Sequence(lambda n: n + 1)
    status = MessageStatus.ACTIVE


class ChatBlockFactory(DjangoModelFactory):
    class Meta:
        model = ChatBlock

    blocker = factory.SubFactory(UserFactory)
    blocked_type = ParticipantType.USER
    blocked_id = factory.LazyFunction(lambda: factory.Faker._get_faker().uuid4())
