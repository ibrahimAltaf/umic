"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type Item = {
  id: string;
  title: string;
  item_type: string;
  priority: string;
  status: string;
  kanban_column: string;
  explanation?: string;
  suggested_action?: string;
  matter_id?: string;
};

const COLUMNS = [
  {
    id: "inbox",
    label: "Inbox",
    hint: "New arrivals",
    accent: "border-t-teal-600",
    header: "bg-teal-50/80 dark:bg-teal-950/30",
  },
  {
    id: "in_progress",
    label: "Working",
    hint: "In progress",
    accent: "border-t-sky-600",
    header: "bg-sky-50/80 dark:bg-sky-950/30",
  },
  {
    id: "review",
    label: "Needs review",
    hint: "Second look",
    accent: "border-t-amber-500",
    header: "bg-amber-50/80 dark:bg-amber-950/30",
  },
  {
    id: "done",
    label: "Done",
    hint: "Resolved",
    accent: "border-t-emerald-600",
    header: "bg-emerald-50/80 dark:bg-emerald-950/30",
  },
] as const;

export default function ReviewQueuePage() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => apiGet<Item[]>("/api/v1/review-queue"),
  });

  const move = useMutation({
    mutationFn: ({ id, kanban_column }: { id: string; kanban_column: string }) =>
      apiSend(`/api/v1/review-queue/${id}`, "PATCH", {
        kanban_column,
        status: kanban_column === "done" ? "resolved" : "open",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const byColumn = useMemo(() => {
    const map: Record<string, Item[]> = {
      inbox: [],
      in_progress: [],
      review: [],
      done: [],
    };
    for (const item of data) {
      const col = map[item.kanban_column] ? item.kanban_column : "inbox";
      map[col].push(item);
    }
    return map;
  }, [data]);

  const activeItem = data.find((i) => i.id === activeId) ?? null;
  const openCount = data.filter((i) => i.kanban_column !== "done").length;

  function onDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function onDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const id = String(e.active.id);
    const overId = e.over?.id ? String(e.over.id) : null;
    if (!overId) return;

    let targetCol = overId;
    if (!COLUMNS.some((c) => c.id === overId)) {
      const overItem = data.find((i) => i.id === overId);
      targetCol = overItem?.kanban_column ?? "";
    }
    const item = data.find((i) => i.id === id);
    if (!item || !targetCol || item.kanban_column === targetCol) return;
    move.mutate({ id, kanban_column: targetCol });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations board"
        title="Review queue"
        description="Drag cards between columns. Unassigned mail, documents, conflicts, and billing exceptions land here."
        actions={
          <>
            <Badge tone={openCount ? "warning" : "success"}>{openCount} open</Badge>
            <Button asChild variant="outline" size="sm">
              <Link href="/emails">Emails</Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/integrations">Sync</Link>
            </Button>
          </>
        }
      />

      {isLoading ? (
        <div className="umic-panel p-10 text-center text-sm text-muted-foreground">
          Loading board…
        </div>
      ) : data.length === 0 ? (
        <EmptyState
          title="Queue is clear"
          description="Sync Gmail or Drive to generate review items for records that need a matter."
          action={
            <Button asChild>
              <Link href="/integrations">Sync sources</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
          >
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {COLUMNS.map((col) => (
                <KanbanColumn
                  key={col.id}
                  column={col}
                  items={byColumn[col.id] ?? []}
                  onSelect={setSelected}
                  selectedId={selected?.id}
                />
              ))}
            </div>
            <DragOverlay>
              {activeItem ? <KanbanCard item={activeItem} dragging /> : null}
            </DragOverlay>
          </DndContext>

          <aside className="umic-panel h-fit p-5 xl:sticky xl:top-20">
            <p className="umic-eyebrow">Card detail</p>
            {selected ? (
              <div className="mt-3 space-y-3">
                <h3 className="font-display text-lg font-semibold leading-snug">
                  {selected.title}
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  <Badge
                    tone={
                      selected.priority === "high"
                        ? "danger"
                        : selected.priority === "medium"
                          ? "warning"
                          : "neutral"
                    }
                  >
                    {selected.priority}
                  </Badge>
                  <Badge>{selected.item_type.replaceAll("_", " ")}</Badge>
                  <Badge tone="neutral">{selected.kanban_column}</Badge>
                </div>
                {selected.explanation ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {selected.explanation}
                  </p>
                ) : null}
                {selected.suggested_action ? (
                  <div className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-sm">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Suggested
                    </p>
                    <p className="mt-1">{selected.suggested_action}</p>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-2 pt-2">
                  {selected.matter_id ? (
                    <Button size="sm" asChild>
                      <Link href={`/matters/${selected.matter_id}`}>Open matter</Link>
                    </Button>
                  ) : null}
                  {COLUMNS.filter((c) => c.id !== selected.kanban_column).map((c) => (
                    <Button
                      key={c.id}
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        move.mutate({ id: selected.id, kanban_column: c.id });
                        setSelected({ ...selected, kanban_column: c.id });
                      }}
                    >
                      Move to {c.label}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                Select a card to see explanation and move actions.
              </p>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function KanbanColumn({
  column,
  items,
  onSelect,
  selectedId,
}: {
  column: (typeof COLUMNS)[number];
  items: Item[];
  onSelect: (item: Item) => void;
  selectedId?: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-[420px] flex-col rounded-xl border border-border/80 border-t-4 bg-muted/20 shadow-sm transition",
        column.accent,
        isOver && "ring-2 ring-primary/30 bg-primary/5",
      )}
    >
      <div className={cn("rounded-t-[0.65rem] px-3 py-3", column.header)}>
        <div className="flex items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold tracking-tight">{column.label}</h3>
            <p className="text-[11px] text-muted-foreground">{column.hint}</p>
          </div>
          <span className="rounded-full bg-background/80 px-2 py-0.5 text-xs font-semibold tabular-nums shadow-sm">
            {items.length}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2.5">
        {items.map((item) => (
          <DraggableCard
            key={item.id}
            item={item}
            selected={selectedId === item.id}
            onSelect={() => onSelect(item)}
          />
        ))}
        {items.length === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed px-3 py-8 text-center text-xs text-muted-foreground">
            Drop cards here
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DraggableCard({
  item,
  selected,
  onSelect,
}: {
  item: Item;
  selected: boolean;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
  });

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={onSelect}
      className={cn(isDragging && "opacity-40")}
    >
      <KanbanCard item={item} selected={selected} />
    </div>
  );
}

function KanbanCard({
  item,
  selected,
  dragging,
}: {
  item: Item;
  selected?: boolean;
  dragging?: boolean;
}) {
  return (
    <article
      className={cn(
        "cursor-grab rounded-lg border bg-card p-3 shadow-sm transition active:cursor-grabbing",
        selected && "ring-2 ring-primary/40 border-primary/30",
        dragging && "shadow-lift scale-[1.02]",
        "hover:shadow-md",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug">{item.title}</p>
        <Badge
          tone={
            item.priority === "high"
              ? "danger"
              : item.priority === "medium"
                ? "warning"
                : "neutral"
          }
        >
          {item.priority}
        </Badge>
      </div>
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {item.item_type.replaceAll("_", " ")}
      </p>
      {item.explanation ? (
        <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">{item.explanation}</p>
      ) : null}
    </article>
  );
}
