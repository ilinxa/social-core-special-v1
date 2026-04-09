/**
 * Chat Page Object Models.
 *
 * Global chat route: /chat
 * Business chat route: /bconsole/[slug]/chat
 * Platform chat route: /pconsole/chat
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

/** Main chat layout — sidebar + message view. */
export class ChatPage extends BasePage {
  // --- Sidebar ---
  readonly sidebarHeading: Locator;
  readonly newConversationButton: Locator;
  readonly conversationSearchInput: Locator;
  readonly conversationList: Locator;

  // --- Empty states ---
  readonly noConversationsMessage: Locator;
  readonly selectConversationMessage: Locator;

  // --- Connection banner ---
  readonly connectionBanner: Locator;

  constructor(page: Page) {
    super(page);

    // Sidebar
    this.sidebarHeading = page.getByRole('heading', { name: /^chat$/i });
    this.newConversationButton = page.getByRole('button', { name: /new conversation/i }).or(
      page.getByRole('button', { name: /new message/i }),
    );
    this.conversationSearchInput = page.getByPlaceholder(/search conversations/i);
    this.conversationList = page.getByRole('listbox', { name: /conversations/i });

    // Empty states
    this.noConversationsMessage = page.getByText(/no conversations yet/i);
    this.selectConversationMessage = page.getByText(/select a conversation/i);

    // Connection banner
    this.connectionBanner = page.getByTestId('connection-banner');
  }

  async goto(): Promise<void> {
    await this.page.goto('/chat');
  }

  async gotoBusinessChat(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/chat`);
  }

  async gotoPlatformChat(): Promise<void> {
    await this.page.goto('/pconsole/chat');
  }

  /** Get a conversation item by name text. */
  getConversationItem(name: string | RegExp): Locator {
    return this.conversationList.getByRole('option', { name });
  }
}

/** Message view — header, messages, compose bar. */
export class MessageViewPanel extends BasePage {
  // --- Header ---
  readonly conversationName: Locator;
  readonly searchButton: Locator;
  readonly settingsButton: Locator;
  readonly backButton: Locator;

  // --- Messages ---
  readonly messageLog: Locator;
  readonly emptyMessagesText: Locator;

  // --- Compose ---
  readonly messageInput: Locator;
  readonly sendButton: Locator;

  // --- Attachments ---
  readonly attachmentButton: Locator;

  // --- Entity sender ---
  readonly entitySenderIndicator: Locator;

  // --- Request banner ---
  readonly requestBanner: Locator;
  readonly requestAcceptButton: Locator;
  readonly requestIgnoreButton: Locator;

  constructor(page: Page) {
    super(page);

    // Header
    this.conversationName = page.getByTestId('conversation-name');
    this.searchButton = page.getByTestId('search-messages-button');
    this.settingsButton = page.getByTestId('conversation-settings-button');
    this.backButton = page.getByTestId('chat-back-button');

    // Messages
    this.messageLog = page.getByRole('log', { name: /messages/i });
    this.emptyMessagesText = page.getByText(/send a message to start/i);

    // Compose
    this.messageInput = page.getByPlaceholder(/type a message/i);
    // Send button: match by aria-label="Send message" on the compose bar button
    this.sendButton = page.getByRole('button', { name: /send/i });

    // Attachments
    this.attachmentButton = page.getByTestId('attachment-button');

    // Entity sender
    this.entitySenderIndicator = page.getByTestId('entity-sender-indicator');

    // Request banner
    this.requestBanner = page.getByTestId('request-banner');
    this.requestAcceptButton = this.requestBanner.getByRole('button', { name: /accept/i });
    this.requestIgnoreButton = this.requestBanner.getByRole('button', { name: /ignore/i });
  }
}

/** Chat request list in sidebar. */
export class ChatRequestsPanel extends BasePage {
  readonly requestList: Locator;
  readonly requestHeading: Locator;

  constructor(page: Page) {
    super(page);
    this.requestList = page.getByTestId('chat-request-list');
    this.requestHeading = page.getByRole('heading', { name: /message requests/i });
  }

  getAcceptButton(conversationId: string): Locator {
    return this.page.getByTestId(`chat-request-${conversationId}`).getByTestId('accept-request');
  }

  getIgnoreButton(conversationId: string): Locator {
    return this.page.getByTestId(`chat-request-${conversationId}`).getByTestId('ignore-request');
  }
}

/** Message search panel (slide-in from right). */
export class MessageSearchPanel extends BasePage {
  readonly panel: Locator;
  readonly searchInput: Locator;
  readonly emptyMessage: Locator;
  readonly noResultsMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.panel = page.getByTestId('message-search-panel');
    this.searchInput = this.panel.getByPlaceholder(/search messages/i);
    this.emptyMessage = page.getByText(/type to search messages/i);
    this.noResultsMessage = page.getByText(/no messages found/i);
  }

  getSearchResult(resultId: string): Locator {
    return this.page.getByTestId(`search-result-${resultId}`);
  }
}

/** Conversation settings sheet. */
export class ConversationSettingsSheet extends BasePage {
  readonly title: Locator;
  readonly participantList: Locator;
  readonly addParticipantButton: Locator;
  readonly participantsHeading: Locator;

  constructor(page: Page) {
    super(page);
    this.title = page.getByRole('heading', { name: /group settings|conversation settings/i });
    this.participantList = page.getByTestId('participant-list');
    this.addParticipantButton = page.getByTestId('add-participant-button');
    this.participantsHeading = page.getByRole('heading', { name: /participants/i });
  }
}

/** New conversation dialog. */
export class NewConversationDialog extends BasePage {
  readonly title: Locator;
  readonly userSearchInput: Locator;
  readonly groupNameInput: Locator;
  readonly createButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    super(page);
    this.title = page.getByRole('heading', { name: /new conversation/i });
    this.userSearchInput = page.getByPlaceholder(/search users/i);
    this.groupNameInput = page.getByPlaceholder(/enter group name/i);
    this.createButton = page.getByRole('button', { name: /^create$/i });
    this.cancelButton = page.getByRole('button', { name: /^cancel$/i });
  }
}

/** Reaction picker and bar. */
export class ReactionControls extends BasePage {
  readonly reactionBar: Locator;
  readonly addReactionButton: Locator;
  readonly reactionPicker: Locator;

  constructor(page: Page) {
    super(page);
    this.reactionBar = page.getByTestId('reaction-bar');
    this.addReactionButton = page.getByTestId('reaction-add-button');
    this.reactionPicker = page.getByTestId('reaction-picker');
  }

  getReactionBadge(reaction: string): Locator {
    return this.page.getByTestId(`reaction-badge-${reaction}`);
  }

  getPickerReaction(reaction: string): Locator {
    return this.page.getByTestId(`reaction-${reaction}`);
  }
}

/** Attachment grid within a message. */
export class AttachmentGrid extends BasePage {
  readonly grid: Locator;

  constructor(page: Page) {
    super(page);
    this.grid = page.getByTestId('attachment-grid');
  }

  getAttachment(index: number): Locator {
    return this.page.getByTestId(`attachment-${index}`);
  }
}

/** Delivery status indicators (own messages only). */
export class DeliveryStatus extends BasePage {
  readonly sent: Locator;
  readonly delivered: Locator;
  readonly seen: Locator;
  readonly seenCount: Locator;

  constructor(page: Page) {
    super(page);
    this.sent = page.getByTestId('delivery-sent');
    this.delivered = page.getByTestId('delivery-delivered');
    this.seen = page.getByTestId('delivery-seen');
    this.seenCount = page.getByTestId('delivery-seen-count');
  }
}
