"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const accessToken = useAuthStore((s) => s.accessToken);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (isHydrated && accessToken) {
      router.replace("/dashboard");
    }
  }, [accessToken, isHydrated, router]);

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      await login(values.email, values.password);
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Unable to sign in. Check API connectivity.");
      }
    }
  });

  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-sidebar text-sidebar-foreground lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-signal/25 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-primary/40 blur-3xl" />
          <div className="absolute inset-0 umic-grid-noise opacity-30" />
        </div>
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sidebar-foreground/60">
            UMIC
          </p>
          <h1 className="mt-6 max-w-md font-display text-5xl font-bold leading-[1.05] tracking-tight">
            Matter-centered intelligence for the whole file.
          </h1>
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-sidebar-foreground/70">
            Gmail, Dropbox, Drive, billing, and review — one workspace keyed to the matter.
          </p>
        </div>
        <ol className="relative space-y-4 text-sm text-sidebar-foreground/75">
          {[
            "Associate mail & documents to matters",
            "Approve time, expenses, and mileage",
            "Export T&E sheets with source links",
          ].map((item, i) => (
            <li key={item} className="flex gap-3">
              <span className="mt-0.5 font-display text-xs font-semibold tabular-nums text-sidebar-foreground/45">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="border-l border-sidebar-foreground/20 pl-3 leading-snug">
                {item}
              </span>
            </li>
          ))}
        </ol>
      </div>

      <div className="relative flex items-center justify-center px-4 py-16">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="umic-panel relative w-full max-w-md p-8"
        >
          <p className="umic-eyebrow lg:hidden">UMIC</p>
          <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use your workspace credentials to open the intelligence center.
          </p>

          <form className="mt-8 space-y-4" onSubmit={onSubmit} noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" {...form.register("email")} />
              {form.formState.errors.email ? (
                <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
              {form.formState.errors.password ? (
                <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
              ) : null}
            </div>
            {error ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}
            <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? "Signing in…" : "Enter workspace"}
            </Button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
