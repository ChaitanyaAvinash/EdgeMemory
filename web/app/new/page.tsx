"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { PageHeader } from "@/components/motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";

const EXAMPLE = {
  requester_id: "E-402",
  cost_centre: "CC-MACH",
  vendor_name: "Nizam Pumps",
  amount_raw: "1.9L",
  quotes_attached: 1,
  justification: "Line 3 band hai, coolant pump seized. Need pump assemblies today. Budget over but line cannot stay down.",
  email_thread: "From: maintenance@kaveri\nLine 3 stopped at 02:10, log MNT-5530.",
  attachment_text: "",
};

export default function NewRequestPage() {
  const router = useRouter();
  const [form, setForm] = useState({ ...EXAMPLE });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: k === "quotes_attached" ? Number(e.target.value) : e.target.value });

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const v = await api.submit(form);
      router.push(`/cases/${v.request.id}?demo=1`);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Intake" title="A new {request}">
      Write it the way people do: amounts like 1.9L, Hinglish, a messy email thread. EdgeMemory extracts the facts,
      runs the checks and recalls precedents. Synthetic data only; the example is pre-filled.
    </PageHeader>
    <Card className="stage-in max-w-3xl [animation-delay:300ms]">
      <CardHeader>
        <CardTitle>Purchase request</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="flex flex-col gap-1">Requester<Input value={form.requester_id} onChange={set("requester_id")} /></label>
          <label className="flex flex-col gap-1">Cost centre<Input value={form.cost_centre} onChange={set("cost_centre")} /></label>
          <label className="flex flex-col gap-1">Quotes attached<Input type="number" min={0} value={form.quotes_attached} onChange={set("quotes_attached")} /></label>
          <label className="flex flex-col gap-1 sm:col-span-2">Vendor<Input value={form.vendor_name} onChange={set("vendor_name")} /></label>
          <label className="flex flex-col gap-1">Amount (as written)<Input value={form.amount_raw} onChange={set("amount_raw")} /></label>
        </div>
        <label className="flex flex-col gap-1">Justification<Textarea value={form.justification} onChange={set("justification")} /></label>
        <label className="flex flex-col gap-1">Email thread<Textarea value={form.email_thread} onChange={set("email_thread")} /></label>
        <label className="flex flex-col gap-1">Attachment text (certificate OCR)<Textarea value={form.attachment_text} onChange={set("attachment_text")} /></label>
        <div className="flex items-center gap-3">
          <Button disabled={busy} onClick={submit}>{busy ? "Checking, recalling and composing from past cases…" : "Submit"}</Button>
          {busy && <span className="text-xs text-muted-foreground">This takes 20–60 seconds: extraction, recall, verification and reflect.</span>}
        </div>
        {error && <p className="text-destructive">{error}</p>}
      </CardContent>
    </Card>
    </div>
  );
}
