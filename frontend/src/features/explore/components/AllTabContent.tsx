"use client";

import { ArrowRight, ChevronDown, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useExploreCombined } from "@/features/explore/hooks/use-explore-queries";
import { BusinessCard } from "./BusinessCard";
import { UserCard } from "./UserCard";

interface AllTabContentProps {
  query: string;
  isAuthenticated: boolean;
}

export function AllTabContent({ query, isAuthenticated }: AllTabContentProps) {
  const { data, isLoading } = useExploreCombined(
    { q: query || undefined },
    isAuthenticated,
  );

  const [bizOpen, setBizOpen] = useState(true);
  const [usersOpen, setUsersOpen] = useState(true);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Businesses Section */}
      <section className="rounded-lg border">
        <button
          type="button"
          onClick={() => setBizOpen((v) => !v)}
          className="flex w-full items-center justify-between p-4"
        >
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold">Businesses</h2>
            <span className="text-xs text-muted-foreground">
              ({data.businesses_count})
            </span>
          </div>
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform ${
              bizOpen ? "rotate-180" : ""
            }`}
          />
        </button>

        <div
          className={`grid transition-[grid-template-rows] duration-200 ${
            bizOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          }`}
        >
          <div className="overflow-hidden">
            <div className="max-h-112 overflow-y-auto px-4 pb-4">
              {data.businesses.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {data.businesses.map((biz) => (
                    <BusinessCard key={biz.id} business={biz} />
                  ))}
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  {query ? "No businesses found" : "No businesses yet"}
                </p>
              )}
              {data.businesses_count > 6 && (
                <div className="mt-3 text-center">
                  <Button variant="ghost" size="sm" asChild>
                    <Link
                      href={`/explore?tab=businesses${query ? `&q=${encodeURIComponent(query)}` : ""}`}
                    >
                      See all {data.businesses_count}
                      <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Users Section (auth-gated) */}
      {isAuthenticated && (
        <section className="rounded-lg border">
          <button
            type="button"
            onClick={() => setUsersOpen((v) => !v)}
            className="flex w-full items-center justify-between p-4"
          >
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">Users</h2>
              <span className="text-xs text-muted-foreground">
                ({data.users_count})
              </span>
            </div>
            <ChevronDown
              className={`h-4 w-4 text-muted-foreground transition-transform ${
                usersOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          <div
            className={`grid transition-[grid-template-rows] duration-200 ${
              usersOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="overflow-hidden">
              <div className="max-h-112 overflow-y-auto px-4 pb-4">
                {data.users.length > 0 ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {data.users.map((u) => (
                      <UserCard key={u.id} user={u} />
                    ))}
                  </div>
                ) : (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    {query ? "No users found" : "No users yet"}
                  </p>
                )}
                {data.users_count > 6 && (
                  <div className="mt-3 text-center">
                    <Button variant="ghost" size="sm" asChild>
                      <Link
                        href={`/explore?tab=users${query ? `&q=${encodeURIComponent(query)}` : ""}`}
                      >
                        See all {data.users_count}
                        <ArrowRight className="ml-1 h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
