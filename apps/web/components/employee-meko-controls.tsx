"use client";

import { useState } from "react";
import { apiRequest, ApiError, type EmployeeResponse, type MemoryFact, type UpdateEmployeeRequest } from "@openhuman/api-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export function EmployeeMekoSettings({employee, onSave}: {employee: EmployeeResponse; onSave: (data: UpdateEmployeeRequest) => void}) {
  const [instructions, setInstructions] = useState(employee.custom_instructions || "");
  return <details className="space-y-3"><summary className="cursor-pointer text-sm font-medium">Extra instructions and memory</summary>
    <div className="mt-3 space-y-2"><Label htmlFor="employee-extra-instructions">Extra instructions</Label><Textarea id="employee-extra-instructions" value={instructions} maxLength={12000} onChange={event => setInstructions(event.target.value)} onBlur={() => {if (instructions !== (employee.custom_instructions || "")) onSave({custom_instructions:instructions});}} /></div>
    <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={employee.auto_memory} onChange={event => onSave({auto_memory:event.target.checked})} />Remember useful facts from saved conversations</label>
  </details>;
}

export function MemoryActions({orgId, employeeId, fact, onSaved}: {orgId: string; employeeId: string; fact?: MemoryFact; onSaved: () => void}) {
  const [busy,setBusy] = useState(false);
  async function change(kind: "remember" | "correct" | "forget") {
    let text: string | null = null;
    if(kind === "forget") {
      if(!window.confirm("Forget this fact and withdraw its tracked company copies? Old transcripts may still contain it.")) return;
    } else {
      text = window.prompt(kind === "remember" ? "What should this employee remember?" : "Correct this remembered fact:", fact?.data || fact?.memory || "");
      if(!text?.trim()) return;
    }
    setBusy(true);
    try {
      const base = `/api/organizations/${orgId}/memory/facts`;
      await apiRequest(kind === "remember" ? base : `${base}/${fact!.id}${kind === "forget" ? `?employee_id=${employeeId}` : ""}`, {
        method: kind === "remember" ? "POST" : kind === "correct" ? "PATCH" : "DELETE",
        ...(kind !== "forget" ? {body:JSON.stringify({employee_id:employeeId,text, ...(kind === "remember" ? {operation_id:crypto.randomUUID()} : {})})} : {}),
      });
      toast.success(kind === "forget" ? "Memory forgotten" : "Memory saved and checked");
      onSaved();
    } catch(error) {toast.error(error instanceof ApiError ? error.messageText : "Memory change could not be confirmed.");}
    finally {setBusy(false);}
  }
  return fact ? <div className="ml-auto flex gap-1"><Button size="sm" variant="ghost" disabled={busy} onClick={() => void change("correct")}>Correct</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void change("forget")}>Forget</Button></div> : <Button size="sm" variant="outline" disabled={busy} onClick={() => void change("remember")}>Remember a fact</Button>;
}
