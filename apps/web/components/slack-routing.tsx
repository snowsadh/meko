"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  apiRequest,
  ApiError,
  useEmployeesListEmployeesRoute,
} from "@openhuman/api-client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

type Decision = { company: boolean; employee_ids: string[]; reason: string };
type Chunk = Decision & {
  id: string;
  status: string;
  error: string | null;
  created_at: string;
  messages: { user_id: string; text: string; channel_id: string; ts: string }[];
  deliveries: Record<
    string,
    {
      status: string;
      source_id?: string;
      conversation_id?: string;
      reason?: string;
      error?: string;
    }
  >;
};
type Setup = {
  app_configured: boolean;
  gateway_enabled: boolean;
  listener_connected: boolean;
  memory_delivery_enabled: boolean;
  connected: boolean;
  oauth_redirect_uri: string;
  required_scopes: string[];
  required_events: string[];
};
const errorText = (error: unknown) =>
  error instanceof ApiError
    ? error.messageText
    : "The request could not be completed.";

export function SlackRouting({
  orgId,
  employeeId,
}: {
  orgId: string;
  employeeId: string;
}) {
  const base = `/api/organizations/${orgId}/slack`;
  const { data: employees = [] } = useEmployeesListEmployeesRoute(orgId);
  const employeeName = (id: string) =>
    employees.find((employee) => employee.id === id)?.name ||
    "Removed employee";
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [decision, setDecision] = useState<Decision | null>(null);
  const { data: setup } = useQuery({
    queryKey: ["slack-setup", orgId, employeeId],
    queryFn: () => apiRequest<Setup>(`${base}/setup?employee_id=${employeeId}`),
    refetchInterval: 8000,
    retry: false,
  });
  const {
    data: chunks = [],
    error,
    refetch,
  } = useQuery({
    queryKey: ["slack-routing", orgId],
    queryFn: () => apiRequest<Chunk[]>(`${base}/routing`),
    refetchInterval: 8000,
    retry: false,
  });
  return (
    <details className="rounded-xl border p-4">
      <summary className="cursor-pointer text-sm font-medium">
        Company chat routing
      </summary>
      <p className="mt-3 text-sm text-muted-foreground">
        One router chooses where Slack chat belongs. This company-wide log shows
        the original chat, its destination and confirmed delivery. Employee fact
        extraction happens afterward.
      </p>
      {setup && (
        <div className="mt-3 text-xs text-muted-foreground">
          <p>
            Slack app:{" "}
            {setup.app_configured ? "configured" : "missing settings"} ·
            Employee: {setup.connected ? "connected" : "disconnected"}
          </p>
          <p>
            Slack listener:{" "}
            {!setup.gateway_enabled ? "paused" : setup.listener_connected ? "connected" : "not connected"} ·
            Memory delivery:{" "}
            {setup.memory_delivery_enabled ? "enabled" : "paused"}
          </p>
          <details className="mt-2">
            <summary className="cursor-pointer">Slack app setup</summary>
            <p className="mt-2 break-all">
              Register this HTTPS redirect URL: {setup.oauth_redirect_uri}
            </p>
            <p>
              Enable Socket Mode and these bot events:{" "}
              {setup.required_events.join(", ")}
            </p>
            <p>Bot scopes: {setup.required_scopes.join(", ")}</p>
            <p>
              Invite the employee to each channel it should read. Reconnect
              after changing app scopes.
            </p>
          </details>
        </div>
      )}
      <form
        className="mt-4 space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setDecision(null);
          try {
            setDecision(
              await apiRequest<Decision>(`${base}/routing/preview`, {
                method: "POST",
                body: JSON.stringify({ text, employee_id: employeeId }),
              }),
            );
          } catch (error) {
            toast.error(errorText(error));
          } finally {
            setBusy(false);
          }
        }}
      >
        <label htmlFor="routing-preview" className="text-sm">
          Try a chat chunk
        </label>
        <Textarea
          id="routing-preview"
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={16000}
          required
        />
        <p className="text-xs text-muted-foreground">
          Calls OpenAI to choose destinations. Does not send this preview to
          Slack or Meko.
        </p>
        <Button type="submit" size="sm" variant="outline" disabled={busy || !text.trim()}>
          {busy ? "Checking…" : "Check destinations"}
        </Button>
      </form>
      {decision && (
        <div className="mt-3 rounded-lg bg-muted p-3 text-sm">
          <p>
            Company: {decision.company ? "yes" : "no"} · Employees selected:{" "}
            {decision.employee_ids.length}
          </p>
          <p className="mt-1">{decision.reason}</p>
          {decision.employee_ids.length > 0 && (
            <p className="mt-1 break-all text-xs">
              {decision.employee_ids.map(employeeName).join(", ")}
            </p>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {errorText(error)}
        </p>
      )}
      {!error && !chunks.length && (
        <p className="mt-4 text-sm text-muted-foreground">
          No Slack chunks received yet.
        </p>
      )}
      <div className="mt-4 space-y-3">
        {chunks.map((chunk) => (
          <article key={chunk.id} className="rounded-lg border p-3 text-sm">
            <p className="text-xs text-muted-foreground">
              {new Date(chunk.created_at).toLocaleString()} ·{" "}
              {chunk.status.replaceAll("_", " ")}
            </p>
            <p className="mt-2">
              {chunk.reason || "Waiting for a routing decision."}
            </p>
            {chunk.reason && (
              <p className="mt-1 text-xs text-muted-foreground">
                Company: {chunk.company ? "yes" : "no"} · Employees selected:{" "}
                {chunk.employee_ids.length}
              </p>
            )}
            {chunk.error && (
              <p role="alert" className="mt-2 text-destructive">
                {chunk.error}
              </p>
            )}
            {chunk.status === "awaiting_memory" && (
              <p className="mt-2 text-xs text-muted-foreground">
                Decision saved. Waiting for memory delivery to be enabled.
              </p>
            )}
            <details className="mt-2">
              <summary className="cursor-pointer">
                Source chat and deliveries
              </summary>
              {chunk.messages.map((message, index) => (
                <div
                  key={index}
                  className="mt-3 whitespace-pre-wrap break-words"
                >
                  <a
                    className="text-xs underline"
                    href={`https://app.slack.com/archives/${encodeURIComponent(message.channel_id)}/p${encodeURIComponent(message.ts.replace(".", ""))}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {message.user_id} · Open in Slack
                  </a>
                  <p>{message.text}</p>
                </div>
              ))}
              {Object.entries(chunk.deliveries).map(
                ([destination, delivery]) => (
                  <p
                    key={destination}
                    className="mt-3 break-all text-xs text-muted-foreground"
                  >
                    {destination.startsWith("employee:")
                      ? employeeName(destination.slice(9))
                      : "Company"}
                    : {delivery.status}
                    {delivery.source_id
                      ? ` · source ${delivery.source_id}`
                      : ""}
                    {delivery.conversation_id
                      ? ` · conversation ${delivery.conversation_id}`
                      : ""}
                    {delivery.reason ? ` · ${delivery.reason}` : ""}
                    {delivery.error ? ` · ${delivery.error}` : ""}
                  </p>
                ),
              )}
            </details>
            {chunk.status === "failed" && (
              <Button
                className="mt-3"
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await apiRequest(`${base}/routing/${chunk.id}/retry`, {
                      method: "POST",
                    });
                    await refetch();
                  } catch (error) {
                    toast.error(errorText(error));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Retry remaining deliveries
              </Button>
            )}
          </article>
        ))}
      </div>
    </details>
  );
}
