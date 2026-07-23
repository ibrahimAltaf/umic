"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiGet, apiSend } from "@/lib/api-client";

type Conn = {
  id: string;
  provider: string;
  account_label: string;
  status: string;
  last_error?: string;
  last_successful_sync_at?: string | null;
};

type GoogleStatus = {
  configured: boolean;
  api_key_configured: boolean;
  redirect_uri?: string;
  dropbox_configured?: boolean;
  dropbox_oauth_configured?: boolean;
};

export default function IntegrationsClient() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const [banner, setBanner] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<unknown>(null);
  const [dropboxToken, setDropboxToken] = useState("");

  const { data = [], isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => apiGet<Conn[]>("/api/v1/integrations"),
  });
  const { data: status } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => apiGet<GoogleStatus>("/api/v1/integrations/google/status"),
  });

  useEffect(() => {
    const g = params.get("google");
    if (g === "connected") {
      setBanner(`Google connected: ${params.get("email") || params.get("provider")}`);
      qc.invalidateQueries({ queryKey: ["integrations"] });
    } else if (g === "error") {
      setBanner(`Google connect failed: ${params.get("message") || "unknown error"}`);
    }
    const d = params.get("dropbox");
    if (d === "connected") {
      setBanner("Dropbox connected via OAuth");
      qc.invalidateQueries({ queryKey: ["integrations"] });
    } else if (d === "error") {
      setBanner(`Dropbox connect failed: ${params.get("message") || "unknown error"}`);
    }
  }, [params, qc]);

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["integrations"] });
    qc.invalidateQueries({ queryKey: ["emails"] });
    qc.invalidateQueries({ queryKey: ["documents"] });
    qc.invalidateQueries({ queryKey: ["review-queue"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const connect = useMutation({
    mutationFn: (provider: string) =>
      apiSend<{ authorize_url: string }>(
        `/api/v1/integrations/google/connect?provider=${provider}`,
        "POST",
      ),
    onSuccess: (res) => {
      window.location.href = res.authorize_url;
    },
  });

  const disconnect = useMutation({
    mutationFn: (provider: string) =>
      apiSend(`/api/v1/integrations/google/${provider}/disconnect`, "POST"),
    onSuccess: () => invalidateAll(),
  });

  const syncGmail = useMutation({
    mutationFn: (full: boolean) =>
      apiSend(
        `/api/v1/integrations/google/gmail/sync?max_results=${full ? 500 : 100}&full=${full}`,
        "POST",
      ),
    onSuccess: (res) => {
      setLastResult(res);
      const r = res as { imported?: number; scanned?: number; full?: boolean };
      setBanner(
        `Gmail sync done — scanned ${r.scanned ?? 0}, imported ${r.imported ?? 0}${r.full ? " (full)" : ""}`,
      );
      invalidateAll();
    },
  });

  const syncDrive = useMutation({
    mutationFn: (full: boolean) =>
      apiSend(
        `/api/v1/integrations/google/drive/sync?max_results=${full ? 500 : 100}&full=${full}`,
        "POST",
      ),
    onSuccess: (res) => {
      setLastResult(res);
      const r = res as { imported?: number; scanned?: number; text_extracted?: number; full?: boolean };
      setBanner(
        `Drive sync done — scanned ${r.scanned ?? 0}, imported ${r.imported ?? 0}, text extracted ${r.text_extracted ?? 0}`,
      );
      invalidateAll();
    },
  });

  const connectDropboxEnv = useMutation({
    mutationFn: () => apiSend("/api/v1/integrations/dropbox/connect-env", "POST"),
    onSuccess: (res) => {
      setLastResult(res);
      setBanner("Dropbox connected from server token");
      invalidateAll();
    },
  });

  const connectDropboxPaste = useMutation({
    mutationFn: () =>
      apiSend("/api/v1/integrations/dropbox/connect-token", "POST", {
        access_token: dropboxToken.trim(),
      }),
    onSuccess: (res) => {
      setLastResult(res);
      setBanner("Dropbox connected with pasted token");
      setDropboxToken("");
      invalidateAll();
    },
  });

  const connectDropboxOAuth = useMutation({
    mutationFn: () =>
      apiSend<{ authorize_url: string }>("/api/v1/integrations/dropbox/oauth/start", "POST"),
    onSuccess: (res) => {
      window.location.href = res.authorize_url;
    },
  });

  const syncDropbox = useMutation({
    mutationFn: (full: boolean) =>
      apiSend(`/api/v1/integrations/dropbox/sync?limit=${full ? 1000 : 200}&full=${full}`, "POST"),
    onSuccess: (res) => {
      setLastResult(res);
      setBanner(`Dropbox sync done — imported ${(res as { imported?: number }).imported ?? 0} files`);
      invalidateAll();
    },
  });

  const extractBatch = useMutation({
    mutationFn: () => apiSend("/api/v1/documents/extract-batch", "POST"),
    onSuccess: (res) => {
      setLastResult(res);
      const r = res as { extracted?: number; failed?: number; scanned?: number };
      setBanner(
        `Text extract done — scanned ${r.scanned ?? 0}, extracted ${r.extracted ?? 0}, failed ${r.failed ?? 0}`,
      );
      invalidateAll();
    },
  });

  const busy =
    syncGmail.isPending ||
    syncDrive.isPending ||
    syncDropbox.isPending ||
    connectDropboxEnv.isPending ||
    connectDropboxPaste.isPending ||
    connectDropboxOAuth.isPending ||
    extractBatch.isPending;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-3xl font-semibold tracking-tight">Integrations</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Connect Google and Dropbox once. Use Sync for a quick pass, or Full history when you want a deeper mailbox / Drive import (can take a few minutes).
        </p>
      </div>

      {banner ? (
        <div className="rounded-md border bg-accent/40 px-4 py-3 text-sm">{banner}</div>
      ) : null}

      <div className="rounded-lg border bg-card/90 p-4 text-sm shadow-panel">
        <p className="font-medium">Status</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge tone={status?.configured ? "success" : "danger"}>
            Google OAuth {status?.configured ? "ready" : "missing"}
          </Badge>
          <Badge tone={status?.api_key_configured ? "success" : "warning"}>
            Google API key {status?.api_key_configured ? "loaded" : "missing"}
          </Badge>
          <Badge tone={status?.dropbox_configured ? "success" : "warning"}>
            Dropbox env token {status?.dropbox_configured ? "present" : "missing"}
          </Badge>
        </div>
      </div>

      <div className="rounded-lg border bg-card/90 p-5 shadow-panel space-y-3">
        <h3 className="font-semibold">Google Sheets (T&amp;E export)</h3>
        <p className="text-sm text-muted-foreground">
          Connect the <code className="text-xs">google_sheets</code> provider below before using
          Export T&amp;E on a matter file. Same Google OAuth app — pick Sheets when connecting.
        </p>
      </div>

      <div className="rounded-lg border bg-card/90 p-5 shadow-panel space-y-3">
        <h3 className="font-semibold">Document text extraction</h3>
        <p className="text-sm text-muted-foreground">
          Pull plain text from Google Docs / PDFs already synced from Drive (OCR-lite).
        </p>
        <Button
          size="sm"
          variant="outline"
          disabled={busy || extractBatch.isPending}
          onClick={() => extractBatch.mutate()}
        >
          {extractBatch.isPending ? "Extracting…" : "Extract Drive text (batch)"}
        </Button>
      </div>

      <div className="rounded-lg border bg-card/90 p-5 shadow-panel space-y-3">
        <h3 className="font-semibold">Dropbox access</h3>
        <p className="text-sm text-muted-foreground">
          Connect with OAuth (app key + secret), paste a token, or use the server .env token.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={!status?.dropbox_oauth_configured || busy}
            onClick={() => connectDropboxOAuth.mutate()}
          >
            Connect Dropbox OAuth
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!status?.dropbox_configured || busy}
            onClick={() => connectDropboxEnv.mutate()}
          >
            Use .env token
          </Button>
        </div>
        <Input
          type="password"
          placeholder="Or paste sl.u...."
          value={dropboxToken}
          onChange={(e) => setDropboxToken(e.target.value)}
        />
        <Button
          size="sm"
          variant="outline"
          disabled={dropboxToken.trim().length < 10 || busy}
          onClick={() => connectDropboxPaste.mutate()}
        >
          Connect pasted token
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {isLoading
          ? null
          : data.map((c) => {
              const isGoogle = c.provider.startsWith("google") || c.provider === "gmail";
              const connected = c.status === "connected";
              return (
                <div key={c.id} className="rounded-lg border bg-card/90 p-5 shadow-panel">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        {c.provider}
                      </p>
                      <h3 className="font-semibold">{c.account_label}</h3>
                    </div>
                    <Badge tone={connected ? "success" : "warning"}>{c.status}</Badge>
                  </div>
                  {c.last_successful_sync_at ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Last sync: {new Date(c.last_successful_sync_at).toLocaleString()}
                    </p>
                  ) : null}
                  {c.last_error ? (
                    <p className="mt-2 text-xs text-destructive">{c.last_error}</p>
                  ) : null}

                  <div className="mt-4 flex flex-wrap gap-2">
                    {isGoogle && !connected ? (
                      <Button
                        size="sm"
                        disabled={!status?.configured || connect.isPending}
                        onClick={() => connect.mutate(c.provider)}
                      >
                        Connect Google
                      </Button>
                    ) : null}
                    {c.provider === "gmail" && connected ? (
                      <>
                        <Button size="sm" disabled={busy} onClick={() => syncGmail.mutate(false)}>
                          {syncGmail.isPending ? "Syncing…" : "Sync emails"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy}
                          onClick={() => syncGmail.mutate(true)}
                        >
                          Full history (500)
                        </Button>
                      </>
                    ) : null}
                    {c.provider === "google_drive" && connected ? (
                      <>
                        <Button size="sm" disabled={busy} onClick={() => syncDrive.mutate(false)}>
                          {syncDrive.isPending ? "Syncing…" : "Sync Drive"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy}
                          onClick={() => syncDrive.mutate(true)}
                        >
                          Full history (500)
                        </Button>
                      </>
                    ) : null}
                    {isGoogle && connected ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => disconnect.mutate(c.provider)}
                      >
                        Disconnect
                      </Button>
                    ) : null}
                    {c.provider === "dropbox" && connected ? (
                      <>
                        <Button size="sm" disabled={busy} onClick={() => syncDropbox.mutate(false)}>
                          {syncDropbox.isPending ? "Syncing…" : "Sync Dropbox"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy}
                          onClick={() => syncDropbox.mutate(true)}
                        >
                          Full history
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              );
            })}
      </div>

      {lastResult ? (
        <pre className="overflow-auto rounded-lg border bg-muted/30 p-4 text-xs">
          {JSON.stringify(lastResult, null, 2)}
        </pre>
      ) : null}
      {connect.error ||
      syncGmail.error ||
      syncDrive.error ||
      syncDropbox.error ||
      connectDropboxEnv.error ||
      connectDropboxPaste.error ||
      extractBatch.error ? (
        <p className="text-sm text-destructive">
          {(connect.error as Error)?.message ||
            (syncGmail.error as Error)?.message ||
            (syncDrive.error as Error)?.message ||
            (syncDropbox.error as Error)?.message ||
            (connectDropboxEnv.error as Error)?.message ||
            (connectDropboxPaste.error as Error)?.message ||
            (extractBatch.error as Error)?.message}
        </p>
      ) : null}
    </div>
  );
}
