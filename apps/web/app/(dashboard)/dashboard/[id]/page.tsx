"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeftIcon,
  ExternalLinkIcon,
  MailIcon,
  PlusIcon,
  Presentation,
  Trash2Icon,
  XIcon,
  Terminal,
  Layers,
  Code,
  Globe,
  Puzzle,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  ApiError,
  apiRequest,
  startSlackInstall,
  useEmployeesGetEmployeeRoute,
  useEmployeesGetMemoriesRoute,
  useEmployeesUpdateEmployeeRoute,
  useEmployeesDeleteEmployeeRoute,
  useEmployeesSetStatus,
  getEmployeesListEmployeesRouteQueryKey,
  getEmployeesGetEmployeeRouteQueryKey,
  useMcpListMcpConnectors,
  useMcpListEmployeeMcpConnections,
  useMcpCreateMcpConnection,
  useMcpDeleteMcpConnection,
  getMcpListEmployeeMcpConnectionsQueryKey,
} from "@openhuman/api-client";
import type { UpdateEmployeeRequest } from "@openhuman/api-client";
import { useOrgStore } from "@/stores/org";
import { getStatusConfig, EMPLOYEE_TYPE_LABELS } from "@/types/employee";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BrandLogo } from "@/components/brand-logos";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { SourceManager } from "@/components/source-manager";
import { MemoryConnection } from "@/components/memory-connection";
import { EmployeeActivity } from "@/components/employee-notebook";
import { EmployeeMekoSettings, MemoryActions } from "@/components/employee-meko-controls";

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span
        className={cn(
          "text-sm font-medium text-foreground",
          mono && "font-mono",
        )}
      >
        {value}
      </span>
    </div>
  );
}

type EditableField = "name" | "role";
const MEMORY_EXPLORER_PAGE_SIZE = 4;

export default function EmployeeDetailPage() {
  const { id: empId } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const orgId = useOrgStore((s) => s.orgId);

  // Dialog visibility states
  const [showDiscordDialog, setShowDiscordDialog] = useState(false);
  const [showClickupDialog, setShowClickupDialog] = useState(false);
  const [showMcpTokenDialog, setShowMcpTokenDialog] = useState(false);
  const [memoryFilter, setMemoryFilter] = useState("");
  const [memoryPage, setMemoryPage] = useState(1);

  // Input states for dialogs
  const [discordToken, setDiscordToken] = useState("");
  const [discordClientId, setDiscordClientId] = useState("");
  const [clickupToken, setClickupToken] = useState("");
  const [mcpTokenValue, setMcpTokenValue] = useState("");
  const [mcpTokenSlug, setMcpTokenSlug] = useState("");
  const [mcpServerUrl, setMcpServerUrl] = useState("");

  // Local connection states loaded from localStorage
  const [localDiscordConnected, setLocalDiscordConnected] = useState(false);
  const [localClickupConnected, setLocalClickupConnected] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && empId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocalDiscordConnected(
        localStorage.getItem(`openhuman_discord_connected_${empId}`) === "true"
      );
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocalClickupConnected(
        localStorage.getItem(`openhuman_clickup_connected_${empId}`) === "true"
      );
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDiscordToken(localStorage.getItem(`openhuman_discord_token_${empId}`) || "");
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDiscordClientId(localStorage.getItem(`openhuman_discord_client_id_${empId}`) || "");
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setClickupToken(localStorage.getItem(`openhuman_clickup_token_${empId}`) || "");
    }
  }, [empId]);

  const handleConnectDiscord = useCallback(() => { toast.error("Discord delivery is not configured in this build."); }, []);

  const handleDisconnectDiscord = useCallback(() => {
    if (!empId) return;
    localStorage.removeItem(`openhuman_discord_connected_${empId}`);
    localStorage.removeItem(`openhuman_discord_token_${empId}`);
    localStorage.removeItem(`openhuman_discord_client_id_${empId}`);
    setLocalDiscordConnected(false);
    setDiscordToken("");
    setDiscordClientId("");
    toast.success("Discord bot disconnected.");
  }, [empId]);

  const handleConnectClickup = useCallback(() => { toast.error("ClickUp delivery is not configured in this build."); }, []);

  const handleDisconnectClickup = useCallback(() => {
    if (!empId) return;
    localStorage.removeItem(`openhuman_clickup_connected_${empId}`);
    localStorage.removeItem(`openhuman_clickup_token_${empId}`);
    setLocalClickupConnected(false);
    setClickupToken("");
    toast.success("ClickUp workspace disconnected.");
  }, [empId]);

  const handleConnectMcpOAuth = useCallback(async (slug: string) => {
    toast.error(
      `${slug} OAuth install is not wired in this backend yet. Use a token/manual connector if available.`,
    );
  }, []);

  const {
    data: apiEmployee,
    isLoading,
    isError,
    error,
  } = useEmployeesGetEmployeeRoute(orgId ?? "", empId, {
    query: { enabled: !!(orgId && empId) },
  });
  const {
    data: memoryExplorer,
    isLoading: memoryExplorerLoading,
    isError: memoryExplorerFailed,
    error: memoryExplorerError,
  } = useEmployeesGetMemoriesRoute(
    orgId ?? "",
    empId,
    { page: memoryPage, limit: MEMORY_EXPLORER_PAGE_SIZE, query: memoryFilter },
    { query: { enabled: !!(orgId && empId && apiEmployee?.meko_datapack_id), retry: false } },
  );

  const employee = apiEmployee
    ? {
        id: apiEmployee.id,
        orgId: apiEmployee.org_id,
        name: apiEmployee.name,
        employeeType: apiEmployee.employee_type ?? null,
        role: apiEmployee.role ?? "",
        specialization: apiEmployee.specialization ?? "",
        duties: (apiEmployee.duties ?? []) as string[],
        status: apiEmployee.status,
        hasDiscord: apiEmployee.has_discord_token || localDiscordConnected,
        hasSlack: apiEmployee.has_slack_token,
        hasClickup: localClickupConnected,
        slackTeamName: apiEmployee.slack_team_name ?? null,
        deployedAt: apiEmployee.created_at,
      }
    : null;

  const updateMutation = useEmployeesUpdateEmployeeRoute();
  const deleteMutation = useEmployeesDeleteEmployeeRoute();
  const statusMutation = useEmployeesSetStatus();

  const invalidate = useCallback(() => {
    if (!orgId) return;
    queryClient.invalidateQueries({
      queryKey: getEmployeesListEmployeesRouteQueryKey(orgId),
    });
    queryClient.invalidateQueries({
      queryKey: getEmployeesGetEmployeeRouteQueryKey(orgId, empId),
    });
  }, [orgId, empId, queryClient]);

  const doUpdate = useCallback(
    (data: UpdateEmployeeRequest) => {
      if (!orgId) return;
      updateMutation.mutate(
        { orgId, empId, data },
        {
          onSuccess: () => invalidate(),
          onError: (error) => toast.error(error instanceof ApiError ? error.messageText : "Could not save employee settings."),
        },
      );
    },
    [orgId, empId, updateMutation, invalidate],
  );

  const searchParams = useSearchParams();

  useEffect(() => {
    const slack = searchParams.get("slack");
    if (slack === "connected") {
      toast.success("Slack workspace connected successfully!");
    } else if (slack === "error") {
      const reason = searchParams.get("reason") || "unknown error";
      toast.error(`Slack connection failed: ${reason}`);
    }
    if (slack) {
      const next = new URL(window.location.href);
      next.searchParams.delete("slack");
      next.searchParams.delete("reason");
      window.history.replaceState({}, "", next.toString());
    }
  }, [searchParams]);

  useEffect(() => {
    const mcpOauth = searchParams.get("mcp_oauth");
    const connector = searchParams.get("connector");
    if (mcpOauth === "connected") {
      toast.success(`${connector === "gmail" ? "Gmail" : connector || "MCP"} connected successfully!`);
      if (orgId && empId) {
        queryClient.invalidateQueries({
          queryKey: getMcpListEmployeeMcpConnectionsQueryKey(orgId, empId),
        });
      }
    } else if (mcpOauth === "error") {
      const reason = searchParams.get("reason") || "unknown error";
      toast.error(`Connection failed: ${reason}`);
    }
    if (mcpOauth) {
      const next = new URL(window.location.href);
      next.searchParams.delete("mcp_oauth");
      next.searchParams.delete("connector");
      next.searchParams.delete("reason");
      next.searchParams.delete("employee_id");
      window.history.replaceState({}, "", next.toString());
    }
  }, [searchParams, orgId, empId, queryClient]);

  const [editingField, setEditingField] = useState<EditableField | null>(null);
  const [draftValue, setDraftValue] = useState("");
  const [dutyInput, setDutyInput] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Config card local state (save on blur, not on every keystroke)
  const [localName, setLocalName] = useState("");
  const [localRole, setLocalRole] = useState("");
  const [localSpecialization, setLocalSpecialization] = useState("");

  // Slack credentials config state removed — fixed mode uses env-based credentials

  const {
    data: connectors,
    isLoading: connectorsLoading,
  } = useMcpListMcpConnectors(orgId ?? "", { query: { enabled: !!orgId } });

  const {
    data: mcpConnectionsData,
    isLoading: mcpConnectionsLoading,
    refetch: refetchMcpConnections,
  } = useMcpListEmployeeMcpConnections(orgId ?? "", empId, { query: { enabled: !!(orgId && empId) } });

  const deleteMcpConnectionMutation = useMcpDeleteMcpConnection();
  const createMcpConnectionMutation = useMcpCreateMcpConnection();

  const handleConnectMcpToken = useCallback(async () => {
    if (!orgId || !empId || !mcpTokenSlug) return;
    if (!mcpTokenValue.trim()) {
      toast.error("Please enter an access token");
      return;
    }

    const connInfo = connectors?.find((c) => c.slug === mcpTokenSlug);
    const authTypes = connInfo?.auth_types ?? [connInfo?.auth_type ?? ""];
    const selectedAuthType = authTypes.find((t) => t === "pat_bearer" || t === "api_key_header") ?? undefined;
    const requiresCustomServerUrl = connInfo?.requires_custom_server_url === true;

    if (requiresCustomServerUrl && !mcpServerUrl.trim()) {
      toast.error("Please enter the MCP server URL");
      return;
    }

    try {
      await createMcpConnectionMutation.mutateAsync({
        orgId,
        empId,
        slug: mcpTokenSlug,
        data: {
          credential: mcpTokenValue.trim(),
          auth_type: selectedAuthType,
          server_url: requiresCustomServerUrl ? mcpServerUrl.trim() : undefined,
          org_wide: false,
        },
      });
      setShowMcpTokenDialog(false);
      setMcpTokenValue("");
      setMcpTokenSlug("");
      setMcpServerUrl("");
      toast.success(`${mcpTokenSlug === "notion" ? "Notion" : mcpTokenSlug} connected successfully!`);
      refetchMcpConnections();
    } catch (err: unknown) {
      toast.error(
        err instanceof ApiError ? err.messageText : `Failed to connect ${mcpTokenSlug}`,
      );
    }
  }, [orgId, empId, mcpTokenSlug, mcpTokenValue, mcpServerUrl, connectors, createMcpConnectionMutation, refetchMcpConnections]);

  const handleConnectNoAuth = useCallback(async (slug: string) => {
    if (!orgId || !empId) return;
    try {
      await createMcpConnectionMutation.mutateAsync({
        orgId,
        empId,
        slug,
        data: { credential: "", org_wide: false },
      });
      toast.success(`${slug} connected successfully!`);
      refetchMcpConnections();
    } catch (err: unknown) {
      toast.error(
        err instanceof ApiError ? err.messageText : `Failed to connect ${slug}`,
      );
    }
  }, [orgId, empId, createMcpConnectionMutation, refetchMcpConnections]);

  const handleDisconnectMcp = useCallback(
    async (slug: string) => {
      if (!orgId || !empId) return;
      try {
        await deleteMcpConnectionMutation.mutateAsync({
          orgId,
          empId,
          slug,
        });
        toast.success(`${slug === "gmail" ? "Gmail" : slug} disconnected successfully!`);
        queryClient.invalidateQueries({
          queryKey: getMcpListEmployeeMcpConnectionsQueryKey(orgId, empId),
        });
      } catch {
        toast.error(`Failed to disconnect ${slug}.`);
      }
    },
    [orgId, empId, deleteMcpConnectionMutation, queryClient]
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocalName(apiEmployee?.name ?? "");
  }, [apiEmployee?.name]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocalRole(apiEmployee?.role ?? "");
  }, [apiEmployee?.role]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocalSpecialization(apiEmployee?.specialization ?? "");
  }, [apiEmployee?.specialization]);

  const displayedMemoryEntries = (memoryExplorer?.memories ?? []).map(entry => ({
    id: entry.id, memory: entry.data || entry.memory || "", updated_at: entry.updated_at, document_ids: [] as string[],
  }));

  const startEdit = useCallback((field: EditableField, value: string) => {
    setDraftValue(value);
    setEditingField(field);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const commitEdit = useCallback(() => {
    if (!editingField || !employee) return;
    const trimmed = draftValue.trim();
    const current = String(employee[editingField] ?? "");
    if (trimmed && trimmed !== current) {
      doUpdate({ [editingField]: trimmed } as UpdateEmployeeRequest);
    }
    setEditingField(null);
    setDraftValue("");
  }, [editingField, draftValue, employee, doUpdate]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-8 px-6 py-6">
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-6 w-48" />
        <Separator />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  // Error state
  if (isError || !employee) {
    const is404 = error instanceof Error && error.message.includes("404");
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-32">
        <p className="text-sm text-muted-foreground">
          {is404 ? "Employee not found." : "Failed to load employee."}
        </p>
        <Button variant="link" onClick={() => router.push("/dashboard")}>
          Back to Team
        </Button>
      </div>
    );
  }

  const statusConfig = getStatusConfig(employee.status);

  const handleAddDuty = () => {
    const trimmed = dutyInput.trim();
    if (!trimmed) return;
    const next = [...employee.duties, trimmed];
    doUpdate({ duties: next });
    setDutyInput("");
  };

  const handleRemoveDuty = (index: number) => {
    const next = employee.duties.filter((_, i) => i !== index);
    doUpdate({ duties: next });
  };

  const handleDelete = () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    if (!orgId) return;
    invalidate();
    deleteMutation.mutate(
      { orgId, empId },
      { onSuccess: () => router.push("/dashboard") },
    );
  };

  return (
    <div className="flex flex-1 flex-col gap-8 px-6 py-6">
      <div className="flex items-center justify-between gap-4">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="w-fit">
            <ArrowLeftIcon />
            Back to Team
          </Button>
        </Link>

        <Button
          variant={confirmDelete ? "destructive" : "ghost"}
          size="sm"
          onClick={handleDelete}
          onBlur={() => setConfirmDelete(false)}
          disabled={deleteMutation.isPending}
        >
          <Trash2Icon />
          {confirmDelete ? "Click again to confirm" : "Delete"}
        </Button>
      </div>

      <div className="flex flex-col gap-1">
        {editingField === "name" ? (
          <Input
            ref={inputRef}
            value={draftValue}
            onChange={(e) => setDraftValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitEdit();
              if (e.key === "Escape") {
                setEditingField(null);
                setDraftValue("");
              }
            }}
            className="text-2xl font-semibold tracking-tight h-auto py-1"
          />
        ) : (
          <h1
            className="cursor-pointer rounded-md px-1 -mx-1 hover:bg-muted/50 transition-colors border border-transparent hover:border-border text-2xl font-semibold tracking-tight text-foreground"
            onClick={() => startEdit("name", employee.name)}
            title="Click to edit"
          >
            {employee.name}
          </h1>
        )}
        {editingField === "role" ? (
          <Input
            ref={inputRef}
            value={draftValue}
            onChange={(e) => setDraftValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitEdit();
              if (e.key === "Escape") {
                setEditingField(null);
                setDraftValue("");
              }
            }}
            className="text-base text-muted-foreground h-auto py-1"
          />
        ) : (
          <span
            className="cursor-pointer rounded-md px-1 -mx-1 hover:bg-muted/50 transition-colors border border-transparent hover:border-border text-base text-muted-foreground"
            onClick={() => startEdit("role", employee.role)}
            title="Click to edit"
          >
            {localRole || "—"}
          </span>
        )}
      </div>

      <Separator />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Info Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-block size-2 shrink-0 rounded-full",
                  statusConfig.dotColor,
                )}
              />
              <h3 className="text-base font-semibold text-foreground">Info</h3>
              {localSpecialization && (
                <span className="ml-auto inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
                  {localSpecialization}
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <InfoRow label="Name" value={employee.name} />
            <InfoRow label="Role" value={localRole || "—"} />
            <InfoRow
              label="Employee Type"
              value={
                employee.employeeType
                  ? (EMPLOYEE_TYPE_LABELS[employee.employeeType] ??
                    employee.employeeType)
                  : "—"
              }
            />
            <InfoRow
              label="Specialization"
              value={localSpecialization || "—"}
            />
            <InfoRow label="Status" value={statusConfig.label} />
            <InfoRow
              label="Deployed"
              value={new Date(employee.deployedAt).toLocaleDateString()}
            />
            <InfoRow
              label="Discord"
              value={employee.hasDiscord ? "Connected" : "Not connected"}
            />
            <InfoRow
              label="Slack"
              value={
                employee.hasSlack && employee.slackTeamName
                  ? `Connected (${employee.slackTeamName})`
                  : employee.hasSlack
                    ? "Connected"
                    : "Not connected"
              }
            />
            <InfoRow
              label="ClickUp"
              value={employee.hasClickup ? "Connected" : "Not connected"}
            />
            {orgId && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Slack Bot</span>
                {employee.hasSlack && employee.slackTeamName ? (
                  <span className="text-sm font-medium text-green-600 dark:text-green-400">
                    Connected ({employee.slackTeamName})
                  </span>
                ) : (
                  <a
                    href="#"
                    onClick={event => { event.preventDefault(); void startSlackInstall(orgId, employee.id).catch(error => toast.error(error instanceof ApiError ? error.messageText : "Could not start Slack installation.")); }}
                    className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                  >
                    <ExternalLinkIcon className="size-3.5" />
                    Add {employee.name} to Slack
                  </a>
                )}
              </div>
            )}
            <InfoRow label="Employee ID" value={employee.id} mono />
          </CardContent>
        </Card>

        {/* Configuration Card */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <h3 className="text-base font-semibold text-foreground">
                Configuration
              </h3>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="employee-name">Name</Label>
                <Input
                  id="employee-name"
                  value={localName}
                  onChange={(e) => setLocalName(e.target.value)}
                  onBlur={() => {
                    if (localName.trim() && localName !== employee.name) {
                      doUpdate({ name: localName.trim() });
                    }
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="employee-role">Role</Label>
                <Input
                  id="employee-role"
                  value={localRole}
                  onChange={(e) => setLocalRole(e.target.value)}
                  onBlur={() => {
                    if (localRole !== employee.role) {
                      doUpdate({ role: localRole.trim() });
                    }
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="employee-specialization">Specialization</Label>
                <Input
                  id="employee-specialization"
                  value={localSpecialization}
                  placeholder="e.g. Technical billing & refunds"
                  onChange={(e) => setLocalSpecialization(e.target.value)}
                  onBlur={() => {
                    if (localSpecialization !== employee.specialization) {
                      doUpdate({
                        specialization: localSpecialization.trim(),
                      });
                    }
                  }}
                />
              </div>

              <EmployeeMekoSettings key={apiEmployee?.id} employee={apiEmployee!} onSave={doUpdate} />
              <Separator />

              {/* Slack Bot Row */}
              {orgId && (
                <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <BrandLogo slug="slack" className="size-5 shrink-0" />
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium text-foreground">
                        Slack Integration
                      </span>
                      {employee.hasSlack && employee.slackTeamName ? (
                        <span className="text-xs text-green-600 dark:text-green-400">
                          Connected to {employee.slackTeamName}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          Install Slack app so {employee.name} can respond to @mentions.
                        </span>
                      )}
                    </div>
                  </div>
                  {employee.hasSlack ? (
                    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      Connected
                    </span>
                  ) : (
                    <a
                      href="#"
                    onClick={event => { event.preventDefault(); void startSlackInstall(orgId, employee.id).catch(error => toast.error(error instanceof ApiError ? error.messageText : "Could not start Slack installation.")); }}
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    >
                      <ExternalLinkIcon className="size-3.5" />
                      Connect
                    </a>
                  )}
                </div>
              )}

              {/* Discord Bot Row */}
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-3">
                  <BrandLogo slug="discord" className="size-5 shrink-0" />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-foreground">
                      Discord Integration
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {employee.hasDiscord
                        ? "Bot token configured"
                        : "No bot token configured"}
                    </span>
                  </div>
                </div>
                {employee.hasDiscord ? (
                  <div className="flex items-center gap-2">
                    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      Connected
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive h-8 px-2"
                      onClick={handleDisconnectDiscord}
                    >
                      Disconnect
                    </Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    onClick={() => setShowDiscordDialog(true)}
                  >
                    Connect
                  </Button>
                )}
              </div>

              {/* ClickUp Row */}
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-3">
                  <BrandLogo slug="clickup" className="size-5 shrink-0" />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-foreground">
                      ClickUp Integration
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {employee.hasClickup
                        ? "Workspace api token configured"
                        : "No workspace token configured"}
                    </span>
                  </div>
                </div>
                {employee.hasClickup ? (
                  <div className="flex items-center gap-2">
                    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      Connected
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive h-8 px-2"
                      onClick={handleDisconnectClickup}
                    >
                      Disconnect
                    </Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    onClick={() => setShowClickupDialog(true)}
                  >
                    Connect
                  </Button>
                )}
              </div>

              <Separator />

              <div className="flex flex-col gap-1.5">
                <Label>Status</Label>
                <Select
                  value={employee.status}
                  onValueChange={(value) => {
                    if (!orgId || !value) return;
                    statusMutation.mutate(
                      { orgId, empId, data: { status: value } },
                      { onSuccess: () => invalidate() },
                    );
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {["active", "inactive", "suspended"].map((status) => (
                        <SelectItem key={status} value={status}>
                          {status}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Duties Card */}
          <Card>
            <CardHeader>
              <h3 className="text-base font-semibold text-foreground">
                Duties
              </h3>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {employee.duties.length > 0 && (
                <div className="flex flex-col gap-2">
                  {employee.duties.map((duty, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2.5"
                    >
                      <span className="min-w-0 flex-1 text-sm text-foreground">
                        {duty}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveDuty(i)}
                        className="mt-0.5 shrink-0 rounded-sm text-muted-foreground hover:text-foreground"
                      >
                        <XIcon className="size-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <Input
                  placeholder="Add a responsibility..."
                  value={dutyInput}
                  onChange={(e) => setDutyInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddDuty();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleAddDuty}
                  className="shrink-0"
                >
                  <PlusIcon />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* MCP Integrations Card */}
          <Card>
            <CardHeader>
              <h3 className="text-base font-semibold text-foreground">
                MCP Integrations
              </h3>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {/* Gmail Connection Row */}
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg border border-border bg-background p-2">
                    <BrandLogo slug="gmail" className="size-full" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-foreground">
                      Gmail / Google Workspace
                    </span>
                    {mcpConnectionsData?.connections?.some(
                      (c) => c.connector_slug === "gmail" && c.status === "connected"
                    ) ? (
                      <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                        Connected
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        Let {employee.name} send, draft, and read emails.
                      </span>
                    )}
                  </div>
                </div>
                {mcpConnectionsData?.connections?.some(
                  (c) => c.connector_slug === "gmail" && c.status === "connected"
                ) ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                    onClick={() => handleDisconnectMcp("gmail")}
                    disabled={deleteMcpConnectionMutation.isPending}
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleConnectMcpOAuth("gmail")}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                  >
                    <ExternalLinkIcon className="size-3.5" />
                    Connect
                  </Button>
                )}
              </div>

              {/* Gamma Connection Row */}
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg border border-border bg-background p-2">
                    <BrandLogo slug="gamma" className="size-full" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-foreground">
                      Gamma Presentations
                    </span>
                    {mcpConnectionsData?.connections?.some(
                      (c) => c.connector_slug === "gamma" && c.status === "connected"
                    ) ? (
                      <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                        Connected
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        Let {employee.name} generate presentations, documents, and web pages.
                      </span>
                    )}
                  </div>
                </div>
                {mcpConnectionsData?.connections?.some(
                  (c) => c.connector_slug === "gamma" && c.status === "connected"
                ) ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                    onClick={() => handleDisconnectMcp("gamma")}
                    disabled={deleteMcpConnectionMutation.isPending}
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleConnectMcpOAuth("gamma")}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                  >
                    <ExternalLinkIcon className="size-3.5" />
                    Connect
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Separator />

      <details className="rounded-xl border border-border p-4"><summary className="cursor-pointer text-sm font-medium">Work and context</summary><div className="mt-4"><EmployeeActivity orgId={orgId!} employeeId={empId} /></div></details>

      {/* Knowledge Sources */}
      <div className="flex flex-col gap-4">
        <SourceManager
          orgId={orgId!}
          employeeId={empId}
          title="Knowledge Sources"
          description={`Add documents to ${employee.name}'s own knowledge.`}
          targetLabel={employee.name}
        />
      </div>

      <div>
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">
                  Memory Explorer
                </h3>
                <p className="text-xs text-muted-foreground">
                  Browse the memories stored for this employee.
                </p>
              </div>
              <div className="w-full sm:w-72">
                <Input
                  value={memoryFilter}
                  onChange={(event) => {
                    setMemoryFilter(event.target.value);
                    setMemoryPage(1);
                  }}
                  placeholder="Search all memories..."
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <MemoryConnection orgId={orgId!} employeeId={empId} connected={!!apiEmployee?.meko_datapack_id} error={apiEmployee?.memory_setup_error} onConnected={invalidate} />
            <MemoryActions orgId={orgId!} employeeId={empId} onSaved={invalidate} />
            {memoryExplorerFailed ? <p role="alert" className="text-sm text-destructive">{memoryExplorerError instanceof ApiError ? memoryExplorerError.messageText : "Could not load memories."}</p> : memoryExplorerLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : displayedMemoryEntries.length ? (
              <>
                <div className="space-y-3">
                  {displayedMemoryEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="rounded-lg border border-border bg-muted/20 p-3"
                    >
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">Meko memory</Badge>
                        <MemoryActions orgId={orgId!} employeeId={empId} fact={{id:entry.id,data:entry.memory}} onSaved={invalidate} />
                      </div>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-foreground">
                        {entry.memory}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                        {entry.updated_at ? (
                          <span>
                            Updated {new Date(entry.updated_at).toLocaleString()}
                          </span>
                        ) : null}
                        {entry.document_ids.length ? (
                          <span>
                            Docs: {entry.document_ids.slice(0, 2).join(", ")}
                            {entry.document_ids.length > 2 ? ` +${entry.document_ids.length - 2}` : ""}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between border-t border-border pt-3">
                  <span className="text-xs text-muted-foreground">
                    Page {memoryExplorer?.page ?? 1} of {memoryExplorer?.total_pages ?? 1}
                    {" · "}
                    {memoryExplorer?.total ?? 0} total memories
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={(memoryExplorer?.page ?? 1) <= 1}
                      onClick={() => setMemoryPage((page) => Math.max(1, page - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={
                        (memoryExplorer?.page ?? 1) >= (memoryExplorer?.total_pages ?? 1)
                      }
                      onClick={() => setMemoryPage((page) => page + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center">
                <p className="text-sm text-muted-foreground">
                  {memoryFilter.trim()
                    ? "No memories match that search."
                    : "No memories have been materialized for this employee yet."}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-col gap-4 border-t border-border pt-8 mt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Puzzle className="size-5 text-muted-foreground" />
            <h3 className="text-base font-semibold text-foreground">
              Featured MCP Integrations Catalog
            </h3>
          </div>
          <Link
            href="/mcp-marketplace"
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
          >
            Browse All Marketplace
            <ExternalLinkIcon className="size-3" />
          </Link>
        </div>
        <p className="text-xs text-muted-foreground -mt-2">
          Connect Model Context Protocol (MCP) data sources and server tools to extend the capabilities of {employee.name}.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
          {[
            {
              slug: "gmail",
              name: "Gmail / Google Workspace",
              description: "Let the agent draft, search, and send email messages.",
            },
            {
              slug: "github",
              name: "GitHub Copilot",
              description: "Access repos, create PRs, search code, and update issues.",
            },
            {
              slug: "notion",
              name: "Notion Workspaces",
              description: "Read, write, query, and synchronize Notion pages.",
            },
            {
              slug: "vercel",
              name: "Vercel Deployments",
              description: "Control serverless setups, logs, and variables.",
            },
            {
              slug: "gamma",
              name: "Gamma Presentations",
              description: "Generate documents, slides, and websites using AI.",
            },
            {
              slug: "n8n",
              name: "n8n Workflows",
              description: "Trigger, inspect, and build workflows on your n8n MCP-enabled instance.",
            },
            {
              slug: "web_search",
              name: "Brave Web Search",
              description: "Query search engines for web index answers.",
            },
            {
              slug: "visualization",
              name: "Visualization Charts",
              description: "Create scatter plots, 3D graphs, histograms, heatmaps, line charts, and network diagrams — no API key required.",
            },
            {
              slug: "canva",
              name: "Canva",
              description: "Generate and export pitch decks and designs — free on every Canva plan.",
            },
            {
              slug: "pitchdeck",
              name: "Pitch Deck Generator",
              description: "Generate styled .pptx pitch decks instantly — free, no API key, no signup.",
            },
            {
              slug: "slack",
              name: "Slack",
              description: "Install the Slack app so this agent can respond to @mentions and DMs.",
            },
          ].map((item) => {
            const isSlack = item.slug === "slack";
            const isConnected = isSlack
              ? Boolean(employee.hasSlack)
              : mcpConnectionsData?.connections?.some(
                  (c) => c.connector_slug === item.slug && c.status === "connected"
                );

            const connInfo = connectors?.find((c) => c.slug === item.slug);
            const authTypes = connInfo?.auth_types ?? [connInfo?.auth_type ?? ""];
            const supportsPaste = authTypes.some((t) => t === "pat_bearer" || t === "api_key_header");
            const isNoneAuth = connInfo?.auth_type === "none";

            return (
              <div
                key={item.slug}
                className="flex flex-col justify-between rounded-xl border border-border/80 bg-muted/20 p-4 transition-all hover:border-primary/30 hover:bg-muted/30"
              >
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted/25 border border-border/70 p-1.5 overflow-hidden">
                      <BrandLogo slug={item.slug} className="size-full" />
                    </div>
                    <span className="text-sm font-semibold text-foreground">
                      {item.name}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {item.description}
                  </p>
                </div>

                <div className="flex items-center justify-between border-t border-border/50 pt-3 mt-4">
                  <span className={`text-[10px] font-semibold ${
                    isConnected ? "text-green-600 dark:text-green-400" : "text-muted-foreground"
                  }`}>
                    {isConnected ? "Connected" : "Disconnected"}
                  </span>

                  {isSlack ? (
                    isConnected ? (
                      <span className="inline-flex h-6 items-center justify-center rounded bg-green-100 px-2.5 text-[10px] font-bold text-green-700 dark:bg-green-900/30 dark:text-green-400 shrink-0">
                        {employee.slackTeamName ?? "Connected"}
                      </span>
                    ) : orgId ? (
                      <a
                        href="#"
                    onClick={event => { event.preventDefault(); void startSlackInstall(orgId, employee.id).catch(error => toast.error(error instanceof ApiError ? error.messageText : "Could not start Slack installation.")); }}
                        className="inline-flex h-6 items-center justify-center rounded bg-primary px-2.5 text-[10px] font-bold text-primary-foreground hover:bg-primary/90 shrink-0"
                      >
                        Connect
                      </a>
                    ) : null
                  ) : isConnected ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 px-2.5 text-[10px] text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                      onClick={() => handleDisconnectMcp(item.slug)}
                      disabled={deleteMcpConnectionMutation.isPending}
                    >
                      Disconnect
                    </Button>
                  ) : supportsPaste ? (
                    <Button
                      onClick={() => {
                        setMcpTokenSlug(item.slug);
                        setMcpTokenValue("");
                        setMcpServerUrl("");
                        setShowMcpTokenDialog(true);
                      }}
                      className="inline-flex h-6 items-center justify-center rounded bg-primary px-2.5 text-[10px] font-bold text-primary-foreground hover:bg-primary/90 shrink-0"
                    >
                      Paste Token
                    </Button>
                  ) : isNoneAuth ? (
                    <Button
                      onClick={() => handleConnectNoAuth(item.slug)}
                      disabled={createMcpConnectionMutation.isPending}
                      className="inline-flex h-6 items-center justify-center rounded bg-primary px-2.5 text-[10px] font-bold text-primary-foreground hover:bg-primary/90 shrink-0"
                    >
                      Connect
                    </Button>
                  ) : (
                    <Button
                      onClick={() => handleConnectMcpOAuth(item.slug)}
                      className="inline-flex h-6 items-center justify-center rounded bg-primary px-2.5 text-[10px] font-bold text-primary-foreground hover:bg-primary/90 shrink-0"
                    >
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Discord Connection Dialog */}
      <Dialog open={showDiscordDialog} onOpenChange={setShowDiscordDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect Discord Bot</DialogTitle>
            <DialogDescription>
              Provide the credentials for your Discord Application Bot to allow {employee?.name} to connect.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="discord-token">Discord Bot Token</Label>
              <Input
                id="discord-token"
                type="password"
                placeholder="MTg0Nj..."
                value={discordToken}
                onChange={(e) => setDiscordToken(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="discord-client-id">Application / Client ID (Optional)</Label>
              <Input
                id="discord-client-id"
                placeholder="1029..."
                value={discordClientId}
                onChange={(e) => setDiscordClientId(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowDiscordDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleConnectDiscord}>
              Confirm Connection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ClickUp Connection Dialog */}
      <Dialog open={showClickupDialog} onOpenChange={setShowClickupDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect ClickUp Workspace</DialogTitle>
            <DialogDescription>
              Enter your Personal API Token to allow {employee?.name} to manage and sync tasks.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="clickup-token">Personal API Token</Label>
              <Input
                id="clickup-token"
                type="password"
                placeholder="pk_..."
                value={clickupToken}
                onChange={(e) => setClickupToken(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowClickupDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleConnectClickup}>
              Confirm Connection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* MCP Token Paste Dialog */}
      <Dialog
        open={showMcpTokenDialog}
        onOpenChange={(open) => {
          setShowMcpTokenDialog(open);
          if (!open) {
            setMcpTokenValue("");
            setMcpTokenSlug("");
            setMcpServerUrl("");
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Connect {mcpTokenSlug === "notion"
                ? "Notion"
                : mcpTokenSlug === "vercel"
                  ? "Vercel"
                  : mcpTokenSlug === "n8n"
                    ? "n8n"
                    : mcpTokenSlug}
            </DialogTitle>
            <DialogDescription>
              {mcpTokenSlug === "n8n"
                ? `Paste your n8n MCP server URL and access token to allow ${employee?.name} to use this integration.`
                : `Paste your access token to allow ${employee?.name} to use this integration.`}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            {connectors?.find((c) => c.slug === mcpTokenSlug)?.requires_custom_server_url ? (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="mcp-server-url">MCP Server URL</Label>
                <Input
                  id="mcp-server-url"
                  type="url"
                  placeholder="https://your-n8n-instance.com/mcp-server/http"
                  value={mcpServerUrl}
                  onChange={(e) => setMcpServerUrl(e.target.value)}
                />
              </div>
            ) : null}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="mcp-token">Access Token</Label>
              <Input
                id="mcp-token"
                type="password"
                placeholder={
                  mcpTokenSlug === "notion"
                    ? "ntn_..."
                    : mcpTokenSlug === "vercel"
                      ? "xxxxxxxxxxxx"
                      : mcpTokenSlug === "n8n"
                        ? "n8n_pat_..."
                        : "Enter token…"
                }
                value={mcpTokenValue}
                onChange={(e) => setMcpTokenValue(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setShowMcpTokenDialog(false); setMcpServerUrl(""); }}>
              Cancel
            </Button>
            <Button
              onClick={handleConnectMcpToken}
              disabled={createMcpConnectionMutation.isPending}
            >
              {createMcpConnectionMutation.isPending ? "Connecting…" : "Confirm Connection"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
