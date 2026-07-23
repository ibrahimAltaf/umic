"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, StatTile } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

type GoogleStatus = {
  configured: boolean;
  api_key_configured: boolean;
  redirect_uri?: string;
  dropbox_configured?: boolean;
};

type Conn = {
  provider: string;
  status: string;
  account_label: string;
};

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const { data: status } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => apiGet<GoogleStatus>("/api/v1/integrations/google/status"),
  });
  const { data: integrations = [] } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => apiGet<Conn[]>("/api/v1/integrations"),
  });

  const connected = integrations.filter((i) => i.status === "connected").length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="System settings"
        description="Live environment status for this UMIC instance. Integration credentials live in server .env."
        actions={
          <Button asChild variant="outline">
            <Link href="/integrations">Manage integrations</Link>
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile
          label="Google OAuth"
          value={status?.configured ? "Ready" : "Missing"}
          tone={status?.configured ? "ok" : "warn"}
          hint={status?.redirect_uri}
        />
        <StatTile
          label="API key"
          value={status?.api_key_configured ? "Loaded" : "Missing"}
          tone={status?.api_key_configured ? "ok" : "warn"}
        />
        <StatTile
          label="Connections"
          value={connected}
          hint={`${integrations.length} providers configured`}
          tone="signal"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Signed-in account">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Name</dt>
              <dd className="font-medium">
                {user ? `${user.first_name} ${user.last_name}` : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium">{user?.email ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Roles</dt>
              <dd className="flex flex-wrap justify-end gap-1">
                {(user?.roles ?? []).map((r) => (
                  <Badge key={r.code}>{r.name}</Badge>
                ))}
              </dd>
            </div>
          </dl>
        </Panel>

        <Panel title="Integration health">
          <ul className="space-y-2">
            {integrations.length === 0 ? (
              <li className="text-sm text-muted-foreground">No connections yet.</li>
            ) : (
              integrations.map((c) => (
                <li
                  key={c.provider}
                  className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium capitalize">{c.provider.replaceAll("_", " ")}</p>
                    <p className="text-xs text-muted-foreground">{c.account_label}</p>
                  </div>
                  <Badge tone={c.status === "connected" ? "success" : "warning"}>{c.status}</Badge>
                </li>
              ))
            )}
          </ul>
          <p className="mt-4 text-xs text-muted-foreground">
            Dropbox needs a fresh access token on the Integrations page when you have one.
          </p>
        </Panel>
      </div>
    </div>
  );
}
