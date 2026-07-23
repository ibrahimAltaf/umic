"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

export default function CreateEntityPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: types } = useQuery({
    queryKey: ["entity-types"],
    queryFn: () => apiGet<{ code: string; name: string }[]>("/api/v1/entity-types"),
  });
  const form = useForm({
    defaultValues: {
      entity_type_code: "person",
      legal_name: "",
      display_name: "",
      primary_email: "",
    },
  });
  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiSend<{ id: string }>("/api/v1/entities", "POST", body),
    onSuccess: (e) => {
      qc.invalidateQueries({ queryKey: ["entities"] });
      router.push(`/entities/${e.id}`);
    },
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader
        eyebrow="Master records"
        title="Create entity"
        description="Add a person or organization you can link across matters."
      />
      <form
        className="umic-panel space-y-4 p-6"
        onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
      >
        <div className="space-y-2">
          <Label>Type</Label>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            {...form.register("entity_type_code")}
          >
            {(types ?? []).map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label>Legal name</Label>
          <Input {...form.register("legal_name", { required: true })} />
        </div>
        <div className="space-y-2">
          <Label>Display name</Label>
          <Input {...form.register("display_name")} />
        </div>
        <div className="space-y-2">
          <Label>Email</Label>
          <Input type="email" {...form.register("primary_email")} />
        </div>
        {mutation.error ? (
          <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
        ) : null}
        <Button type="submit" disabled={mutation.isPending}>
          Create entity
        </Button>
      </form>
    </div>
  );
}
