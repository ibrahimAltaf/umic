"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, PageHeader } from "@/components/ui/page";
import { apiGet } from "@/lib/api-client";

type Entity = {
  id: string;
  display_name: string;
  legal_name: string;
  primary_email?: string;
  primary_phone?: string;
  entity_type: { name: string };
  status: string;
};

export default function EntitiesPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["entities", search],
    queryFn: () =>
      apiGet<{ items: Entity[]; total?: number }>(
        `/api/v1/entities?page_size=50${search ? `&search=${encodeURIComponent(search)}` : ""}`,
      ),
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Master records"
        title="Entities"
        description="People and organizations reused across matters — carriers, insureds, counsel, vendors."
        actions={
          <Button asChild>
            <Link href="/entities/new">Create entity</Link>
          </Button>
        }
      />

      <Input
        className="max-w-md bg-card/80"
        placeholder="Search name or email…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">Loading…</div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No entities yet"
          description="Create people and orgs, then link them on matter files."
          action={
            <Button asChild>
              <Link href="/entities/new">Create entity</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((e) => (
            <Link
              key={e.id}
              href={`/entities/${e.id}`}
              className="umic-panel group block p-5 transition hover:-translate-y-0.5 hover:shadow-lift"
            >
              <div className="flex items-start justify-between gap-2">
                <Badge>{e.entity_type.name}</Badge>
                <Badge tone={e.status === "active" ? "success" : "neutral"}>{e.status}</Badge>
              </div>
              <h3 className="mt-3 font-display text-lg font-semibold group-hover:text-primary">
                {e.display_name}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">{e.legal_name}</p>
              <p className="mt-3 text-xs text-muted-foreground">
                {e.primary_email || e.primary_phone || "No contact on file"}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
