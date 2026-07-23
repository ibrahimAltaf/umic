"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page";
import { apiGet, apiSend } from "@/lib/api-client";

type Ref = {
  matter_types: { code: string; name: string }[];
  statuses: { code: string; name: string }[];
  billing_classifications: { code: string; name: string }[];
};

type Form = {
  name: string;
  matter_type_code: string;
  status_code: string;
  billing_classification_code: string;
  claim_number?: string;
  policy_number?: string;
  case_number?: string;
  property_address?: string;
  hourly_rate?: number;
  is_personal?: boolean;
  is_confidential?: boolean;
  is_privileged?: boolean;
  aliases?: string;
  notes?: string;
};

export default function CreateMatterPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: ref } = useQuery({
    queryKey: ["matter-ref"],
    queryFn: () => apiGet<Ref>("/api/v1/matters/meta/reference"),
  });
  const form = useForm<Form>({
    defaultValues: {
      status_code: "open",
      billing_classification_code: "requires_review",
      matter_type_code: "insurance_appraisal",
    },
  });

  const mutation = useMutation({
    mutationFn: (body: Form) =>
      apiSend<{ id: string }>("/api/v1/matters", "POST", {
        ...body,
        aliases: (body.aliases || "")
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      }),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ["matters"] });
      router.push(`/matters/${m.id}`);
    },
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Matter files"
        title="Create matter"
        description="Approved matter data is authoritative. Imports create discrepancy alerts, not silent overwrites."
      />

      <form
        className="umic-panel space-y-4 p-6"
        onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
      >
        <Field label="Matter name">
          <Input {...form.register("name", { required: true })} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Matter type">
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              {...form.register("matter_type_code")}
            >
              {(ref?.matter_types ?? []).map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              {...form.register("status_code")}
            >
              {(ref?.statuses ?? []).map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Billing classification">
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            {...form.register("billing_classification_code")}
          >
            {(ref?.billing_classifications ?? []).map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Claim number">
            <Input {...form.register("claim_number")} />
          </Field>
          <Field label="Policy number">
            <Input {...form.register("policy_number")} />
          </Field>
          <Field label="Case number">
            <Input {...form.register("case_number")} />
          </Field>
          <Field label="Aliases (comma separated)">
            <Input {...form.register("aliases")} placeholder="Johnson wind, CLM short name" />
          </Field>
        </div>
        <Field label="Property address">
          <Input {...form.register("property_address")} />
        </Field>
        <Field label="Hourly rate">
          <Input type="number" step="0.01" {...form.register("hourly_rate", { valueAsNumber: true })} />
        </Field>
        <div className="flex flex-wrap gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" {...form.register("is_personal")} />
            Personal / restricted
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" {...form.register("is_confidential")} />
            Confidential
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" {...form.register("is_privileged")} />
            Privileged
          </label>
        </div>
        <Field label="Notes">
          <Input {...form.register("notes")} />
        </Field>
        {mutation.error ? (
          <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
        ) : null}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating…" : "Create matter"}
        </Button>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
