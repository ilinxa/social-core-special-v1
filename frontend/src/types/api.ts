/**
 * Shared API response types.
 *
 * Generic types for composing API responses with additional metadata
 * like evaluated permissions from backend policies.
 */

// =============================================================================
// PERMISSION-AWARE RESPONSES
// =============================================================================

/**
 * Generic wrapper for resources that include evaluated permissions.
 *
 * Backend GET detail endpoints inject `_permissions` via PermissionInjectMixin.
 * The permissions are evaluated booleans from Policy.get_viewer_permissions().
 *
 * @example
 * type BusinessAccountWithPerms = BusinessAccount & WithPermissions<BusinessPermissions>;
 */
export type WithPermissions<TPerms extends Record<string, boolean>> = {
  _permissions: TPerms;
};
