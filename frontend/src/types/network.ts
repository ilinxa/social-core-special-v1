/**
 * Network types matching backend API contracts.
 *
 * Backend source: apps.network.serializers
 */

// =============================================================================
// FOLLOW
// =============================================================================

/** Backend: FollowingOutput — user's own following list. */
export type FollowingItem = {
  id: string;
  followee_type: "business" | "platform";
  followee_id: string;
  followee_name: string;
  followee_slug: string | null;
  created_at: string;
};

/** Backend: FollowOutput — followers management (account owners). */
export type FollowerItem = {
  id: string;
  follower: NetworkUser;
  followee_type: string;
  followee_id: string;
  followee_name: string;
  status: string;
  created_at: string;
};

// =============================================================================
// CONNECTION
// =============================================================================

/** Backend: UserConnectionOutput — user↔user connections. */
export type UserConnectionItem = {
  id: string;
  other_user: NetworkUser;
  note: string;
  status: string;
  connected_at: string | null;
  created_at: string;
};

/** Backend: AccountConnectionOutput — account↔account connections. */
export type AccountConnectionItem = {
  id: string;
  other_account: { type: string; id: string; name: string };
  note: string;
  status: string;
  connected_at: string | null;
  created_at: string;
};

// =============================================================================
// SHARED
// =============================================================================

/** Backend: NetworkUserOutput — minimal user info for network lists. */
export type NetworkUser = {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string;
};

/** Backend: NetworkStatsOutput. */
export type NetworkStats = {
  followers_count: number;
  following_count: number;
  connections_count: number;
};
