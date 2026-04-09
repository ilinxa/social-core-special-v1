/**
 * Notification Constants
 * ======================
 * Display config, category labels, and timing constants.
 */

import type { LucideIcon } from "lucide-react";
import {
  Ban,
  Bell,
  CheckCircle,
  Clock,
  ClipboardCheck,
  Handshake,
  Heart,
  HelpCircle,
  KeyRound,
  Lock,
  Mail,
  MessageCircle,
  MessageSquare,
  MessageSquareCheck,
  Newspaper,
  PartyPopper,
  RefreshCw,
  Shield,
  ShieldAlert,
  Tag,
  Timer,
  UserCheck,
  UserPlus,
  Users,
  UsersRound,
  XCircle,
} from "lucide-react";

// =============================================================================
// DISPLAY CONFIG — maps notification_type to icon + title
// =============================================================================

type NotificationDisplayMeta = {
  title: string;
  icon: LucideIcon;
};

export const NOTIFICATION_DISPLAY_CONFIG: Record<string, NotificationDisplayMeta> = {
  // AUTH
  verify_email: { title: "Verify your email", icon: Mail },
  welcome: { title: "Welcome to the platform!", icon: PartyPopper },
  password_reset: { title: "Password reset requested", icon: KeyRound },

  // SECURITY
  password_changed: { title: "Password changed", icon: Lock },
  new_login: { title: "New login detected", icon: Shield },
  suspicious_activity: { title: "Suspicious activity detected", icon: ShieldAlert },

  // MARKETING
  newsletter: { title: "New newsletter", icon: Newspaper },
  promotions: { title: "Special offer available", icon: Tag },

  // TRANSACTIONAL
  transaction_pending_approval: { title: "New request needs your review", icon: ClipboardCheck },
  transaction_invitation_received: { title: "You received an invitation", icon: UserPlus },
  transaction_accepted: { title: "Your request was accepted", icon: CheckCircle },
  transaction_denied: { title: "Your request was denied", icon: XCircle },
  transaction_cancelled: { title: "Transaction cancelled", icon: Ban },
  transaction_expired: { title: "Transaction expired", icon: Timer },
  transaction_expiring_soon: { title: "Request expiring soon", icon: Clock },
  transaction_info_requested: { title: "More information requested", icon: HelpCircle },
  transaction_resubmitted: { title: "Request updated", icon: RefreshCw },

  // SOCIAL (Network)
  new_follower: { title: "New follower", icon: UserPlus },
  follow_request_received: { title: "Follow request received", icon: UserCheck },
  follow_request_accepted: { title: "Follow request accepted", icon: UserCheck },
  connection_request_received: { title: "Connection request", icon: Users },
  connection_accepted: { title: "Connection accepted", icon: Handshake },

  // SOCIAL (Chat)
  chat_message_received: { title: "New chat message", icon: MessageSquare },
  chat_request_received: { title: "Chat request received", icon: MessageCircle },
  chat_request_accepted: { title: "Chat request accepted", icon: MessageSquareCheck },
  chat_group_added: { title: "Added to group chat", icon: UsersRound },
  chat_reaction_received: { title: "Reaction on your message", icon: Heart },
};

/** Fallback for unknown notification types */
export const NOTIFICATION_DEFAULT_META: NotificationDisplayMeta = {
  title: "Notification",
  icon: Bell,
};

/**
 * Get display metadata for a notification type.
 * Falls back to default for unknown types.
 */
export function getNotificationMeta(notificationType: string): NotificationDisplayMeta {
  return NOTIFICATION_DISPLAY_CONFIG[notificationType] ?? NOTIFICATION_DEFAULT_META;
}

// =============================================================================
// CATEGORY LABELS
// =============================================================================

export const NOTIFICATION_CATEGORY_LABELS: Record<string, string> = {
  auth: "Authentication",
  security: "Security",
  transactional: "Transactions",
  marketing: "Marketing",
  social: "Social",
};

// =============================================================================
// TIMING & LIMITS
// =============================================================================

export const NOTIFICATION_SCOPES_POLL_INTERVAL_MS = 60_000;
export const NOTIFICATION_HISTORY_PAGE_SIZE = 50;
export const NOTIFICATION_DROPDOWN_LIMIT = 10;
