"use client";

import { LogOut, Menu, Moon, Search, Sun, UserRound } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";
import { useMobileNav } from "@/components/layout/mobile-nav";

export function AppHeader() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { setOpen } = useMobileNav();
  const [q, setQ] = useState("");

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border/80 bg-background/80 px-4 backdrop-blur-md md:px-8">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-4 w-4" />
      </Button>

      <form
        className="relative max-w-xl flex-1"
        onSubmit={(e) => {
          e.preventDefault();
          const term = q.trim();
          if (term.length >= 2) router.push(`/search?q=${encodeURIComponent(term)}`);
        }}
      >
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search matters, claim #, emails, documents…"
          className="h-10 border-border/70 bg-card/70 pl-9 shadow-sm"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Global search"
        />
      </form>

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
        <div className="hidden items-center gap-2 rounded-full border border-border/80 bg-card/80 px-3 py-1.5 text-sm shadow-sm sm:flex">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-primary">
            <UserRound className="h-3.5 w-3.5" />
          </span>
          <span className="max-w-[160px] truncate font-medium">
            {user ? `${user.first_name} ${user.last_name}` : "Account"}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="bg-card/70"
          onClick={async () => {
            await logout();
            router.replace("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Logout</span>
        </Button>
      </div>
    </header>
  );
}
