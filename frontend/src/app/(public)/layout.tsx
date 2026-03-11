"use client";

import { useAuthStore } from "@/stores/auth-store";
import { Topbar, Sidebar, BottomNavbar } from "@/components/navigation";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitialized = useAuthStore((s) => s.isInitialized);

  // While auth is initializing, show unauthenticated layout to avoid flash
  if (!isInitialized || !isAuthenticated) {
    return (
      <div className="min-h-screen">
        <Topbar variant="public" />
        <main>{children}</main>
      </div>
    );
  }

  // Authenticated users get full nav shell with personal context
  return (
    <>
      <div className="fixed inset-0 flex flex-col">
        <Topbar variant="authenticated" />
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6 pb-20 md:pb-6">
            {children}
          </main>
        </div>
      </div>
      <BottomNavbar />
    </>
  );
}
