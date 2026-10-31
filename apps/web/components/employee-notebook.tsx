"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  apiRequest,
  ApiError,
  type AgentRun,
  type MemoryFact,
  type MemoryPage,
} from "@openhuman/api-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SlackRouting } from "@/components/slack-routing";

const message = (error: unknown) =>
  error instanceof ApiError
    ? error.messageText
    : "The operation could not be completed.";
const factText = (fact: MemoryFact) => fact.data || fact.memory || "";

export function EmployeeMemory({
  orgId,
  employeeId,
  connected,
}: {
  orgId: string;
  employeeId: string;
  connected: boolean;
}) {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [newFact, setNewFact] = useState("");
  const [edit, setEdit] = useState<{ id: string; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const base = `/api/organizations/${orgId}`;
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["meko-memories", orgId, employeeId, page, query],
    queryFn: () =>
      apiRequest<MemoryPage>(
        `${base}/employees/${employeeId}/memories?page=${page}&limit=20${query ? `&q=${encodeURIComponent(query)}` : ""}`,
      ),
    enabled: connected,
    refetchInterval: connected ? 8000 : false,
    retry: false,
  });
  async function mutate(path: string, method: string, body?: unknown) {
    setBusy(true);
    try {
      await apiRequest(`${base}/memory${path}`, {
        method,
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      setNewFact("");
      setEdit(null);
      await client.invalidateQueries({
        queryKey: ["meko-memories", orgId, employeeId],
      });
      await client.invalidateQueries({ queryKey: ["memory-sources"] });
      toast.success(
        method === "DELETE"
          ? "Memory forgotten"
          : path.endsWith("/share")
            ? "Company lesson submitted for indexing"
            : "Memory saved and checked",
      );
    } catch (error) {
      toast.error(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="space-y-5" aria-label="Employee memories">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Remembered facts</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Facts learned by this employee. Company sharing is a separate
            choice.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => void refetch()}
          disabled={!connected}
        >
          Refresh
        </Button>
      </div>
      {!connected ? (
        <p className="text-sm text-muted-foreground">
          Connect employee memory first.
        </p>
      ) : (
        <>
          <form
            className="space-y-2 rounded-xl border bg-muted/20 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              void mutate("/facts", "POST", {
                employee_id: employeeId,
                text: newFact,
                operation_id: crypto.randomUUID(),
              });
            }}
          >
            <Label htmlFor="remember-fact">Remember a fact</Label>
            <Textarea
              id="remember-fact"
              value={newFact}
              onChange={(e) => setNewFact(e.target.value)}
              maxLength={8000}
              placeholder="A fact this employee should remember…"
              required
            />
            <Button type="submit" size="sm" disabled={busy || !newFact.trim()}>
              Remember
            </Button>
          </form>
          <Input
            aria-label="Search remembered facts"
            placeholder="Search remembered facts…"
            value={query}
            onChange={(e) => {
              setPage(1);
              setQuery(e.target.value);
            }}
          />
          {isError ? (
            <p role="alert" className="text-sm text-destructive">
              {message(error)}
            </p>
          ) : isLoading ? (
            <p className="text-sm text-muted-foreground">Loading facts…</p>
          ) : data?.memories.length ? (
            <ul className="divide-y rounded-xl border">
              {data.memories.map((fact) => (
                <li key={fact.id} className="space-y-3 p-4">
                  {edit?.id === fact.id ? (
                    <div className="space-y-2">
                      <Textarea
                        aria-label="Correct this memory"
                        value={edit.text}
                        onChange={(e) =>
                          setEdit({ ...edit, text: e.target.value })
                        }
                      />
                      <p className="text-xs text-muted-foreground">
                        Saving also withdraws old company copies of this fact.
                        Share the corrected version again when ready.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          disabled={busy || !edit.text.trim()}
                          onClick={() =>
                            void mutate(`/facts/${fact.id}`, "PATCH", {
                              employee_id: employeeId,
                              text: edit.text,
                            })
                          }
                        >
                          Save correction
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEdit(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                      {factText(fact) ||
                        "This record has no readable fact text."}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy || !factText(fact)}
                      onClick={() =>
                        setEdit({ id: fact.id, text: factText(fact) })
                      }
                    >
                      Correct
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy || !factText(fact)}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Share this exact lesson with every employee in the company? Your original memory stays in this employee's context.\n\n${factText(fact)}`,
                          )
                        )
                          void mutate(`/facts/${fact.id}/share`, "POST", {
                            employee_id: employeeId,
                            expected_text: factText(fact),
                            confirmed: true,
                          });
                      }}
                    >
                      Share with company
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Forget this fact and withdraw its published company copies? Old conversation history may still contain it.\n\n${factText(fact)}`,
                          )
                        )
                          void mutate(
                            `/facts/${fact.id}?employee_id=${employeeId}`,
                            "DELETE",
                          );
                      }}
                    >
                      Forget
                    </Button>
                  </div>
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer">Record details</summary>
                    <p className="mt-2 break-all font-mono">{fact.id}</p>
                    {fact.created_at && (
                      <p>{new Date(fact.created_at).toLocaleString()}</p>
                    )}
                    <p className="mt-1">
                      Conversation-level activity appears below. A source link
                      is shown only when the service provides it.
                    </p>
                  </details>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
              No matching facts yet. Conversation extraction can take a little
              time.
            </p>
          )}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {data?.total || 0} facts · Page {page}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= (data?.total_pages || 1)}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export function EmployeeActivity({
  orgId,
  employeeId,
}: {
  orgId: string;
  employeeId: string;
}) {
  const client = useQueryClient();
  const [input, setInput] = useState("");
  const [useMemory, setUseMemory] = useState(true);
  const [busy, setBusy] = useState(false);
  const {
    data: runs = [],
    isError,
    error,
  } = useQuery({
    queryKey: ["employee-runs", orgId, employeeId],
    queryFn: () =>
      apiRequest<AgentRun[]>(
        `/api/agent/runs?org_id=${orgId}&employee_id=${employeeId}`,
      ),
    refetchInterval: 5000,
    retry: false,
  });
  return (
    <section className="space-y-5" aria-label="Employee activity">
      <div>
        <h2 className="text-lg font-semibold">Work and context</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Actual requests, replies, recalled sources, and tool results.
        </p>
      </div>
      <details className="rounded-xl border p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Test this employee
        </summary>
        <p className="mt-2 text-sm text-muted-foreground">
          Try a fresh request before using Slack. Connected work tools are
          disabled in this preview.
        </p>
        <form
          className="mt-4 space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            try {
              await apiRequest<AgentRun>("/api/agent/message", {
                method: "POST",
                body: JSON.stringify({
                  org_id: orgId,
                  employee_id: employeeId,
                  message: input,
                  use_meko: useMemory,
                  request_key: crypto.randomUUID(),
                }),
              });
              setInput("");
            } catch (error) {
              toast.error(message(error));
            } finally {
              setBusy(false);
              void client.invalidateQueries({
                queryKey: ["employee-runs", orgId, employeeId],
              });
            }
          }}
        >
          <Label htmlFor="test-employee-request">Request</Label>
          <Textarea
            id="test-employee-request"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={16000}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useMemory}
              onChange={(e) => setUseMemory(e.target.checked)}
            />
            Use saved knowledge
          </label>
          <p className="text-xs text-muted-foreground">
            Switch off for the same-task comparison. That run bypasses memory
            reads and writes.
          </p>
          <Button type="submit" disabled={busy || !input.trim()}>
            {busy ? "Working…" : "Run preview"}
          </Button>
        </form>
      </details>
      <SlackRouting orgId={orgId} employeeId={employeeId} />
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {message(error)}
        </p>
      )}
      {!isError && !runs.length && (
        <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
          No work recorded yet. Connect Slack or try a preview.
        </p>
      )}
      <div className="space-y-4">
        {runs.map((run) => (
          <article key={run.id} className="rounded-xl border p-5">
            <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {run.platform === "slack" ? "Slack" : "Preview"} · {run.status}
                {run.platform === "slack"
                  ? ` · delivery: ${run.delivery_status}`
                  : ""}
              </span>
              <time>{new Date(run.created_at).toLocaleString()}</time>
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm font-medium">
              {run.input}
            </p>
            {run.output && (
              <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed">
                {run.output}
              </p>
            )}
            {run.error && (
              <p role="alert" className="mt-3 text-sm text-destructive">
                {run.error}
              </p>
            )}
            <p className="mt-4 text-xs text-muted-foreground">
              Memory:{" "}
              {run.capture_status === "saved"
                ? "Conversation saved; extracted facts may still be processing."
                : run.capture_status === "pending"
                  ? "Conversation capture pending."
                  : run.capture_status === "skipped"
                    ? "Capture disabled for this run."
                    : run.capture_status === "router"
                      ? "Managed by the company chat router above."
                      : "Capture failed. The conversation is not confirmed saved."}
            </p>
            {run.capture_status === "failed" && (
              <Button
                className="mt-2"
                size="sm"
                variant="outline"
                onClick={async () => {
                  try {
                    await apiRequest(`/api/agent/runs/${run.id}/capture`, {
                      method: "POST",
                    });
                    void client.invalidateQueries({
                      queryKey: ["employee-runs", orgId, employeeId],
                    });
                  } catch (error) {
                    toast.error(message(error));
                  }
                }}
              >
                Retry conversation save
              </Button>
            )}
            <details className="mt-4">
              <summary className="cursor-pointer text-sm">
                Context used ({run.recalled.length})
              </summary>
              {!run.recalled.length && (
                <p className="mt-2 text-sm text-muted-foreground">
                  No sources were supplied to the model for this run.
                </p>
              )}
              <ol className="mt-3 list-decimal space-y-3 pl-5">
                {run.recalled.map((hit, index) => (
                  <li
                    key={`${hit.container_tag}:${hit.provider_result_id}:${index}`}
                    className="text-sm"
                  >
                    <p className="font-medium">
                      {hit.container_tag.replaceAll("_", " ")}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap break-words text-muted-foreground">
                      {hit.content}
                    </p>
                  </li>
                ))}
              </ol>
            </details>
            {run.tools.length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-sm">
                  Tools used ({run.tools.length})
                </summary>
                <ul className="mt-3 space-y-3">
                  {run.tools.map((tool, index) => (
                    <li key={index} className="text-sm">
                      <p className="font-medium">
                        {tool.name} · {tool.status}
                      </p>
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">
                        {JSON.stringify(tool.arguments, null, 2)}
                        {tool.result ? `\n${tool.result}` : ""}
                      </pre>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
