"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, Panel } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";

type SearchResult = {
  query: string;
  matters: { id: string; matter_number: string; name: string; href: string }[];
  entities: { id: string; display_name: string; email?: string; href: string }[];
  emails: { id: string; subject?: string; sender?: string; href: string }[];
  documents: { id: string; file_name: string; source_system: string; href: string }[];
};

function SearchInner() {
  const params = useSearchParams();
  const router = useRouter();
  const initial = params.get("q") || "";
  const [q, setQ] = useState(initial);

  const { data, isFetching, error } = useQuery({
    queryKey: ["search", initial],
    queryFn: () => apiGet<SearchResult>(`/api/v1/search?q=${encodeURIComponent(initial)}`),
    enabled: initial.trim().length >= 2,
  });

  const total =
    (data?.matters.length ?? 0) +
    (data?.entities.length ?? 0) +
    (data?.emails.length ?? 0) +
    (data?.documents.length ?? 0);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Global find"
        title="Search"
        description="Matters, entities, emails, and documents — one query across the workspace."
      />
      <form
        className="flex max-w-2xl gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          router.push(`/search?q=${encodeURIComponent(q.trim())}`);
        }}
      >
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Claim number, matter name, email subject…"
          className="bg-card/80"
          autoFocus
        />
        <Button type="submit">Search</Button>
      </form>
      {error ? <p className="text-sm text-destructive">{(error as Error).message}</p> : null}
      {isFetching ? <p className="text-sm text-muted-foreground">Searching…</p> : null}
      {data ? (
        <>
          <p className="text-xs text-muted-foreground">
            {total} results for “{data.query}”
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <ResultPanel title="Matters" empty="No matters">
              {data.matters.map((m) => (
                <Link
                  key={m.id}
                  href={m.href}
                  className="block rounded-md border px-3 py-2 transition hover:bg-muted/40"
                >
                  <div className="text-xs text-muted-foreground">{m.matter_number}</div>
                  <div className="font-medium">{m.name}</div>
                </Link>
              ))}
            </ResultPanel>
            <ResultPanel title="Entities" empty="No entities">
              {data.entities.map((e) => (
                <Link
                  key={e.id}
                  href={e.href}
                  className="block rounded-md border px-3 py-2 transition hover:bg-muted/40"
                >
                  <div className="font-medium">{e.display_name}</div>
                  <div className="text-xs text-muted-foreground">{e.email || "—"}</div>
                </Link>
              ))}
            </ResultPanel>
            <ResultPanel title="Emails" empty="No emails">
              {data.emails.map((e) => (
                <a
                  key={e.id}
                  href={e.href}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-md border px-3 py-2 transition hover:bg-muted/40"
                >
                  <div className="font-medium">{e.subject || "(no subject)"}</div>
                  <div className="text-xs text-muted-foreground">{e.sender}</div>
                </a>
              ))}
            </ResultPanel>
            <ResultPanel title="Documents" empty="No documents">
              {data.documents.map((d) => (
                <a
                  key={d.id}
                  href={d.href}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-md border px-3 py-2 transition hover:bg-muted/40"
                >
                  <div className="font-medium">{d.file_name}</div>
                  <div className="text-xs text-muted-foreground">{d.source_system}</div>
                </a>
              ))}
            </ResultPanel>
          </div>
        </>
      ) : (
        <Panel title="Tips">
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>Try a claim number or matter name (e.g. Johnson).</li>
            <li>Email subjects and document names are searchable after sync.</li>
            <li>Open a matter file to work emails, docs, and billing together.</li>
          </ul>
        </Panel>
      )}
    </div>
  );
}

function ResultPanel({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: React.ReactNode;
}) {
  const list = Array.isArray(children) ? children : [children];
  const has = list.filter(Boolean).length > 0;
  return (
    <Panel title={title}>
      <div className="space-y-2">
        {has ? children : <p className="text-sm text-muted-foreground">{empty}</p>}
      </div>
    </Panel>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading search…</p>}>
      <SearchInner />
    </Suspense>
  );
}
