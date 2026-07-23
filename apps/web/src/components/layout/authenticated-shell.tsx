"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { MobileNavProvider, useMobileNav } from "@/components/layout/mobile-nav";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

function ShellInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const user = useAuthStore((s) => s.user);
  const { open, setOpen } = useMobileNav();

  useEffect(() => {
    if (!isHydrated) return;
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (!user) {
      fetchMe().catch(() => {
        useAuthStore.getState().clear();
        router.replace("/login");
      });
    }
  }, [accessToken, fetchMe, isHydrated, router, user]);

  if (!isHydrated || !accessToken) {
    return (
      <div
        className="flex min-h-screen flex-col items-center justify-center gap-3"
        suppressHydrationWarning
      >
        <div
          className="h-10 w-10 animate-pulse rounded-full bg-primary/20 ring-2 ring-primary/30"
          suppressHydrationWarning
        />
        <p className="text-sm text-muted-foreground" suppressHydrationWarning>
          Opening workspace…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen" suppressHydrationWarning>
      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px] transition md:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={() => setOpen(false)}
      />
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <main className="relative flex-1 px-4 py-5 md:px-8 md:py-7">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 umic-grid-noise opacity-40" />
          <div className="relative mx-auto max-w-[1400px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

export function AuthenticatedShell({ children }: { children: React.ReactNode }) {
  return (
    <MobileNavProvider>
      <ShellInner>{children}</ShellInner>
    </MobileNavProvider>
  );
}
