"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Email = {
  id: string;
  subject?: string;
  sender?: string;
  snippet?: string;
  direction: string;
  received_at?: string;
  review_status: string;
  classification_confidence?: string;
  matter_name?: string;
  primary_matter_id?: string;
  gmail_message_link?: string;
  attachment_count: number;
};

type MatterOpt = { id: string; name: string; matter_number: string };

export default function EmailsPage() {
  const qc = useQueryClient();
  const [associateFor, setAssociateFor] = useState<string | null>(null);
  const [matterId, setMatterId] = useState("");
  const [filter, setFilter] = useState<"all" | "unassigned" | "linked">("all");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["emails"],
    queryFn: () =>
      apiGet<{ items: Email[]; total: number }>("/api/v1/integrations/emails?page_size=50"),
  });
  const matters = useQuery({
    queryKey: ["matters-opts"],
    queryFn: () => apiGet<{ items: MatterOpt[] }>("/api/v1/matters?page_size=100"),
  });
  const associate = useMutation({
    mutationFn: () =>
      apiSend(`/api/v1/integrations/emails/${associateFor}/associate`, "POST", {
        matter_id: matterId,
      }),
    onSuccess: () => {
      setAssociateFor(null);
      setMatterId("");
      qc.invalidateQueries({ queryKey: ["emails"] });
      qc.invalidateQueries({ queryKey: ["review-queue"] });
    },
  });

  const items = (data?.items ?? []).filter((e) => {
    if (filter === "unassigned") return !e.primary_matter_id;
    if (filter === "linked") return !!e.primary_matter_id;
    return true;
  });
  const unassignedCount = (data?.items ?? []).filter((e) => !e.primary_matter_id).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Emails"
        description="Indexed Gmail with matter association. Unassigned mail feeds the review queue."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link href="/integrations">Sync Gmail</Link>
            </Button>
            <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
              Refresh
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        {(
          [
            ["all", `All (${data?.total ?? 0})`],
            ["unassigned", `Unassigned (${unassignedCount})`],
            ["linked", "Linked"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              filter === id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card/80 text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}

      {associateFor ? (
        <div className="umic-panel flex flex-wrap items-end gap-3 p-4">
          <div className="min-w-[240px] flex-1">
            <p className="text-xs font-medium text-muted-foreground">Link this email to a matter</p>
            <select
              className="mt-1.5 w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={matterId}
              onChange={(e) => setMatterId(e.target.value)}
            >
              <option value="">Select matter…</option>
              {(matters.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.matter_number} — {m.name}
                </option>
              ))}
            </select>
          </div>
          <Button disabled={!matterId || associate.isPending} onClick={() => associate.mutate()}>
            Save association
          </Button>
          <Button variant="ghost" onClick={() => setAssociateFor(null)}>
            Cancel
          </Button>
        </div>
      ) : null}

      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading emails…</div>
      ) : items.length ? (
        <div className="space-y-2">
          {items.map((e) => (
            <article
              key={e.id}
              className="umic-panel flex flex-col gap-3 p-4 transition hover:shadow-lift sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{e.direction}</Badge>
                  <Badge tone={e.primary_matter_id ? "success" : "warning"}>
                    {e.primary_matter_id ? "Linked" : "Unassigned"}
                  </Badge>
                  {e.attachment_count > 0 ? (
                    <Badge tone="neutral">{e.attachment_count} attachments</Badge>
                  ) : null}
                </div>
                <h3 className="mt-2 font-medium leading-snug">
                  {e.gmail_message_link ? (
                    <a
                      href={e.gmail_message_link}
                      target="_blank"
                      rel="noreferrer"
                      className="hover:text-primary hover:underline"
                    >
                      {e.subject || "(no subject)"}
                    </a>
                  ) : (
                    e.subject || "(no subject)"
                  )}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">{e.sender}</p>
                <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{e.snippet}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Matter:{" "}
                  {e.primary_matter_id ? (
                    <Link href={`/matters/${e.primary_matter_id}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                      {e.matter_name}
                    </Link>
                  ) : (
                    "—"
                  )}
                  {e.received_at ? ` · ${new Date(e.received_at).toLocaleString()}` : ""}
                </p>
              </div>
              <Button
                size="sm"
                variant={e.primary_matter_id ? "outline" : "default"}
                onClick={() => {
                  setAssociateFor(e.id);
                  setMatterId(e.primary_matter_id || "");
                }}
              >
                {e.primary_matter_id ? "Reassign" : "Associate"}
              </Button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No emails in this view"
          description="Go to Integrations and run Sync emails — then associate unassigned messages to matters."
          action={
            <Button asChild>
              <Link href="/integrations">Open integrations</Link>
            </Button>
          }
        />
      )}
    </div>
  );
}
