"use client";

import { useState } from "react";
import { apiRequest, ApiError } from "@openhuman/api-client";
import { Button } from "@/components/ui/button";

export function MemoryConnection({
  orgId,
  employeeId,
  connected,
  error,
  onConnected,
}: {
  orgId: string;
  employeeId?: string;
  connected: boolean;
  error?: string | null;
  onConnected?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  if (connected)
    return (
      <p className="text-sm text-muted-foreground">
        {employeeId
          ? "Employee memory connected. Personal context stays separate from company knowledge."
          : "Company knowledge connected. Shared with your AI employees."}
      </p>
    );
  return (
    <div
      className="rounded-xl border border-border bg-muted/30 p-4"
      role="status"
    >
      <p className="text-sm font-medium">
        {employeeId
          ? "Employee memory needs setup"
          : "Company knowledge needs setup"}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        {message ||
          error ||
          "Connect knowledge before uploading documents or starting work."}
      </p>
      <Button
        className="mt-3"
        variant="outline"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setMessage(null);
          try {
            const path = employeeId
              ? `/api/organizations/${orgId}/employees/${employeeId}/memory/connect`
              : `/api/organizations/${orgId}/memory/connect`;
            const result = await apiRequest<{
              meko_datapack_id?: string;
              memory_setup_error?: string;
            }>(path, { method: "POST" });
            if (!result.meko_datapack_id)
              setMessage(
                result.memory_setup_error || "Setup is still pending.",
              );
            onConnected?.();
          } catch (error) {
            setMessage(
              error instanceof ApiError
                ? error.messageText
                : "Setup failed. Try again.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Connecting…" : "Retry setup"}
      </Button>
    </div>
  );
}
