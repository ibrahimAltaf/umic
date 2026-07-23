"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader, Panel } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Doc = {
  id: string;
  file_name: string;
  source_system: string;
  current_path?: string;
  mime_type?: string;
  file_size?: number;
  direct_link?: string;
  review_status: string;
  matter_name?: string;
  primary_matter_id?: string;
  source_modified_at?: string;
  has_text?: boolean;
};

type MatterOpt = { id: string; name: string; matter_number: string };

type DupGroup = {
  file_hash: string;
  count: number;
  files: {
    id: string;
    file_name: string;
    source_system: string;
    path?: string;
  }[];
};

export default function DocumentsPage() {
  const qc = useQueryClient();
  const [associateFor, setAssociateFor] = useState<string | null>(null);
  const [matterId, setMatterId] = useState("");
  const [source, setSource] = useState<"all" | "google_drive" | "dropbox">("all");
  const [showDupes, setShowDupes] = useState(false);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["documents", source],
    queryFn: () =>
      apiGet<{ items: Doc[]; total: number }>(
        `/api/v1/integrations/documents?page_size=50${
          source !== "all" ? `&source_system=${source}` : ""
        }`,
      ),
  });
  const duplicates = useQuery({
    queryKey: ["doc-duplicates"],
    queryFn: () =>
      apiGet<{ group_count: number; duplicate_groups: DupGroup[] }>(
        "/api/v1/documents/duplicates",
      ),
  });
  const matters = useQuery({
    queryKey: ["matters-opts"],
    queryFn: () => apiGet<{ items: MatterOpt[] }>("/api/v1/matters?page_size=100"),
  });
  const associate = useMutation({
    mutationFn: () =>
      apiSend(`/api/v1/integrations/documents/${associateFor}/associate`, "POST", {
        matter_id: matterId,
      }),
    onSuccess: () => {
      setAssociateFor(null);
      setMatterId("");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
  const extract = useMutation({
    mutationFn: (id: string) => apiSend(`/api/v1/documents/${id}/extract`, "POST"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["matter-overview"] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Evidence"
        title="Documents"
        description={`Drive and Dropbox files indexed into UMIC. Duplicate groups: ${duplicates.data?.group_count ?? 0}.`}
        actions={
          <>
            <Button variant="outline" asChild>
              <Link href="/integrations">Sync sources</Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowDupes((v) => !v)}
              disabled={!duplicates.data?.group_count}
            >
              {showDupes ? "Hide duplicates" : "Show duplicates"}
            </Button>
            <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
              Refresh
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "All"],
            ["google_drive", "Google Drive"],
            ["dropbox", "Dropbox"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setSource(id)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
              source === id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card/80 text-muted-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}
      {extract.error ? (
        <p className="text-sm text-destructive">{(extract.error as Error).message}</p>
      ) : null}

      {showDupes ? (
        <Panel title={`Duplicate groups (${duplicates.data?.group_count ?? 0})`}>
          {(duplicates.data?.duplicate_groups ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No hashed duplicates found.</p>
          ) : (
            <ul className="space-y-4">
              {(duplicates.data?.duplicate_groups ?? []).map((g) => (
                <li key={g.file_hash} className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">
                    Hash {g.file_hash.slice(0, 12)}… · {g.count} files
                  </p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {g.files.map((f) => (
                      <li key={f.id} className="flex justify-between gap-2">
                        <span className="font-medium">{f.file_name}</span>
                        <Badge>{f.source_system}</Badge>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      ) : null}

      {associateFor ? (
        <div className="umic-panel flex flex-wrap items-end gap-3 p-4">
          <div className="min-w-[240px] flex-1">
            <p className="text-xs font-medium text-muted-foreground">Associate document to matter</p>
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
            Save
          </Button>
          <Button variant="ghost" onClick={() => setAssociateFor(null)}>
            Cancel
          </Button>
        </div>
      ) : null}

      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading…</div>
      ) : data?.items.length ? (
        <div className="umic-panel overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3">File</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Matter</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((d) => (
                <tr key={d.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3">
                    {d.direct_link ? (
                      <a
                        href={d.direct_link}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium hover:underline"
                      >
                        {d.file_name}
                      </a>
                    ) : (
                      <span className="font-medium">{d.file_name}</span>
                    )}
                    <div className="line-clamp-1 text-xs text-muted-foreground">{d.current_path}</div>
                    {d.has_text ? (
                      <Badge tone="success" className="mt-1">
                        Text extracted
                      </Badge>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <Badge>{d.source_system}</Badge>
                  </td>
                  <td className="px-4 py-3">{d.matter_name || "—"}</td>
                  <td className="px-4 py-3">
                    <Badge tone={d.review_status === "pending" ? "warning" : "success"}>
                      {d.review_status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap justify-end gap-2">
                      {!d.has_text ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={extract.isPending}
                          onClick={() => extract.mutate(d.id)}
                        >
                          Extract
                        </Button>
                      ) : null}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setAssociateFor(d.id);
                          setMatterId(d.primary_matter_id || "");
                        }}
                      >
                        Associate
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No documents yet"
          description="Connect Drive or Dropbox and run Sync — files will appear here for matter association."
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
