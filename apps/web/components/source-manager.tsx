"use client";

import { useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
} from "lucide-react";
import {
  getMemorySourcesQueryKey,
  useDocumentsUploadDocument,
  useEmployeesListEmployeesRoute,
  useMemorySourcesCreateUrl,
  useMemorySourcesDelete,
  useMemorySourcesList,
  useMemorySourcesRetry,
  type CreateUrlMemorySourceRequest,
  type EmployeeResponse,
  type MemorySourceResponse,
} from "@openhuman/api-client";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getSourceStatusClassName, getSourceStatusLabel } from "@/lib/source-status";

const FILE_ACCEPT = ".pdf,.md,.txt,.text,.csv,.json,.html,.htm,.xml";
const SUPPORTED_FORMATS_LABEL = "Supported: PDF and UTF-8 Markdown/text/CSV/JSON/HTML/XML, up to 5 MB each";

interface SourceManagerProps {
  orgId: string;
  employeeId?: string;
  title?: string;
  description?: string;
  compact?: boolean;
  orgLabel?: string;
  targetLabel?: string;
  allowDatasetSelection?: boolean;
}

type DatasetOption = {
  value: string;
  label: string;
  employeeId?: string;
};

function buildDatasetOptions(orgLabel: string, employees: EmployeeResponse[]): DatasetOption[] {
  return [
    { value: "org", label: orgLabel },
    ...employees.map((employee) => ({
      value: employee.id,
      label: employee.name,
      employeeId: employee.id,
    })),
  ];
}

function getDatasetLabel(
  source: MemorySourceResponse,
  datasetLabels: Map<string, string>,
  orgLabel: string,
  targetLabel?: string,
): string {
  if (source.employee_id) {
    return datasetLabels.get(source.employee_id) ?? targetLabel ?? "Employee";
  }
  return targetLabel ?? orgLabel;
}

export function SourceManager({
  orgId,
  employeeId,
  title = "Knowledge Sources",
  description = "Upload documents for this workspace.",
  compact = false,
  orgLabel = "Company DB",
  targetLabel,
  allowDatasetSelection = false,
}: SourceManagerProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isFixedEmployeeView = Boolean(employeeId);
  const isFlexibleDatasetView = allowDatasetSelection && !isFixedEmployeeView;

  const { data: employees = [] } = useEmployeesListEmployeesRoute(orgId, {
    query: { enabled: !!orgId && isFlexibleDatasetView },
  });

  const datasetOptions = useMemo(
    () => buildDatasetOptions(orgLabel, employees),
    [employees, orgLabel],
  );
  const datasetLabels = useMemo(
    () => new Map(datasetOptions.map((option) => [option.value, option.label])),
    [datasetOptions],
  );

  const [filterDataset, setFilterDataset] = useState<string>("all");
  const [targetDataset, setTargetDataset] = useState<string>(employeeId ?? "org");
  const [urlTitle, setUrlTitle] = useState("");
  const [urlValue, setUrlValue] = useState("");

  const queryKey = getMemorySourcesQueryKey(orgId, isFixedEmployeeView ? employeeId : undefined);

  const { data, isLoading, isError } = useMemorySourcesList(
    orgId,
    isFixedEmployeeView ? employeeId : undefined,
    { query: { enabled: !!orgId, refetchInterval: 5000, retry: false } },
  );
  const uploadDocument = useDocumentsUploadDocument();
  const createUrl = useMemorySourcesCreateUrl();
  const deleteSource = useMemorySourcesDelete();
  const retrySource = useMemorySourcesRetry();

  const pending = uploadDocument.isPending || createUrl.isPending;
  const allSources = data ?? [];

  const visibleSources = useMemo(() => {
    let sources = [...allSources];
    if (isFixedEmployeeView) {
      return sources.sort((a, b) => b.created_at.localeCompare(a.created_at));
    }
    if (isFlexibleDatasetView) {
      if (filterDataset === "org") {
        sources = sources.filter((source) => source.employee_id == null);
      } else if (filterDataset !== "all") {
        sources = sources.filter((source) => source.employee_id === filterDataset);
      }
    } else {
      sources = sources.filter((source) => source.employee_id == null);
    }
    return sources.sort((a, b) => b.created_at.localeCompare(a.created_at));
  }, [allSources, filterDataset, isFixedEmployeeView, isFlexibleDatasetView]);

  const selectedTarget = useMemo(() => {
    if (isFixedEmployeeView && employeeId) {
      return { scope: "employee" as const, employeeId };
    }
    if (!isFlexibleDatasetView || targetDataset === "org") {
      return { scope: "org" as const, employeeId: undefined };
    }
    return { scope: "employee" as const, employeeId: targetDataset };
  }, [employeeId, isFixedEmployeeView, isFlexibleDatasetView, targetDataset]);

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey });
  };

  const handleUploadFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    for (const file of Array.from(fileList)) {
      try {
        await uploadDocument.mutateAsync({
          data: {
            file: file as unknown as string,
            organization_id: orgId,
            employee_id: selectedTarget.employeeId as string | undefined,
          },
        });
      } catch {
        toast.error(`Failed to upload ${file.name}`);
      }
    }
    await invalidate();
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCreateUrl = async () => {
    if (!urlValue.trim()) return;
    const payload: CreateUrlMemorySourceRequest = {
      scope: selectedTarget.scope,
      source_url: urlValue.trim(),
      title: urlTitle.trim() || undefined,
      employee_id: selectedTarget.employeeId,
    };
    try {
      await createUrl.mutateAsync({ orgId, data: payload });
      setUrlTitle("");
      setUrlValue("");
      await invalidate();
      toast.success("URL source added.");
    } catch {
      toast.error("Failed to add URL source.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className={compact ? "text-sm font-semibold text-foreground" : "text-base font-semibold text-foreground"}>
          {title}
        </h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      {isFlexibleDatasetView ? (
        <div className="rounded-xl border border-border bg-card/60 p-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2">
              <Label>Browse dataset</Label>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant={filterDataset === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilterDataset("all")}
                >
                  All sources
                </Button>
                {datasetOptions.map((option) => (
                  <Button
                    key={option.value}
                    type="button"
                    variant={filterDataset === option.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterDataset(option.value)}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="target-dataset">Target DB for new source</Label>
              <Select
                value={targetDataset}
                onValueChange={(value) => {
                  if (value) setTargetDataset(value);
                }}
              >
                <SelectTrigger id="target-dataset" className="min-w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {datasetOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      ) : null}

      <Tabs defaultValue="file" className="space-y-4">
        <TabsList>
          <TabsTrigger value="file">Upload file</TabsTrigger>
          <TabsTrigger value="url" disabled title="Meko URL import is not configured">Add URL</TabsTrigger>
        </TabsList>

        <TabsContent value="file" className="space-y-3">
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") fileInputRef.current?.click();
            }}
            className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-border bg-card/40 px-4 py-8 text-center transition-colors hover:border-primary/40"
          >
            {uploadDocument.isPending ? (
              <Spinner className="size-6" />
            ) : (
              <UploadCloud className="size-6 text-muted-foreground/70" />
            )}
            <p className="text-sm font-medium text-foreground">
              Upload supported knowledge files
            </p>
            <p className="text-xs text-muted-foreground">{SUPPORTED_FORMATS_LABEL}</p>
            {!isFixedEmployeeView && !isFlexibleDatasetView ? (
              <p className="text-xs text-muted-foreground">
                New uploads go to {targetLabel ?? orgLabel}.
              </p>
            ) : null}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={FILE_ACCEPT}
            className="hidden"
            onChange={(event) => void handleUploadFiles(event.target.files)}
          />
        </TabsContent>

        <TabsContent value="url" className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="source-url-title">Title</Label>
            <Input
              id="source-url-title"
              value={urlTitle}
              onChange={(e) => setUrlTitle(e.target.value)}
              placeholder="Pricing documentation"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="source-url-value">URL</Label>
            <Input
              id="source-url-value"
              type="url"
              value={urlValue}
              onChange={(e) => setUrlValue(e.target.value)}
              placeholder="https://example.com/docs"
            />
          </div>
          <Button onClick={() => void handleCreateUrl()} disabled={pending || !urlValue.trim()}>
            {createUrl.isPending ? <Loader2 className="animate-spin" /> : <Plus />}
            Add URL source
          </Button>
        </TabsContent>
      </Tabs>

      <div className="space-y-2">
        {isError ? <p role="alert" className="text-sm text-destructive">Could not load knowledge sources.</p> : isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : visibleSources.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
            No sources added yet.
          </div>
        ) : (
          visibleSources.map((source) => (
            <div key={source.id} className="rounded-lg border border-border px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {source.source_type === "url" ? (
                      <Globe className="size-4 text-muted-foreground" />
                    ) : (
                      <FileText className="size-4 text-muted-foreground" />
                    )}
                    <span className="truncate text-sm font-medium text-foreground">
                      {source.title || (source.source_type === "url" ? source.source_url : "Untitled source")}
                    </span>
                    <Badge
                      variant="secondary"
                      className={getSourceStatusClassName(source.status)}
                    >
                      {getSourceStatusLabel(source.status)}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {getDatasetLabel(source, datasetLabels, orgLabel, targetLabel)}
                    </Badge>
                  </div>
                  {source.source_url ? (
                    <a
                      href={source.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-xs text-primary hover:underline"
                    >
                      {source.source_url}
                    </a>
                  ) : source.content_text ? (
                    <p className="line-clamp-3 text-sm text-muted-foreground">{source.content_text}</p>
                  ) : null}
                  {source.error_message ? (
                    <p className="text-xs text-destructive">{source.error_message}</p>
                  ) : null}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  {source.status === "failed" ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => void retrySource.mutateAsync({ orgId, sourceId: source.id }).then(invalidate)}
                      disabled={retrySource.isPending}
                    >
                      <RefreshCw className={retrySource.isPending ? "animate-spin" : ""} />
                    </Button>
                  ) : null}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => void deleteSource.mutateAsync({ orgId, sourceId: source.id }).then(invalidate)}
                    disabled={deleteSource.isPending}
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
