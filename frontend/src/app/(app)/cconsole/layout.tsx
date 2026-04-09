/**
 * CMS Console layout — minimal passthrough.
 * AuthGuard from the parent (app) layout already handles authentication.
 */
export default function CmsConsoleLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
