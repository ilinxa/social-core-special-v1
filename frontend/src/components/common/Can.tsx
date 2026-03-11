/**
 * Declarative permission gate component.
 *
 * Renders children only when `allowed` is true.
 * Used with `_permissions` from backend GET detail responses (Tier 1.5).
 *
 * @example
 * <Can allowed={permissions.can_edit}>
 *   <EditButton />
 * </Can>
 */

interface CanProps {
  allowed: boolean | undefined;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function Can({ allowed, fallback = null, children }: CanProps) {
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
