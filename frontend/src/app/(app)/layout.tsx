"use client";

import { AuthGuard } from "@/components/guards/AuthGuard";
import { Topbar, Sidebar, BottomNavbar } from "@/components/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
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
    </AuthGuard>
  );
}
