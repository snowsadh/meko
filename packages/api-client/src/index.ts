import {
  useMutation,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type QueryOptions<T> = {
  query?: {
    enabled?: boolean;
    refetchInterval?: number | false;
    retry?: boolean;
  };
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(typeof body === "string" ? body : `API request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }

  get messageText(): string {
    if (typeof this.body === "string" && this.body.trim()) {
      return this.body;
    }
    if (this.body && typeof this.body === "object") {
      const detail = (this.body as { detail?: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
      const message = (this.body as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    return this.message;
  }
}

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("oh_token");
}

function clearBrowserAuthState() {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  window.localStorage.removeItem("oh_token");
  document.cookie = "oh_token=; Path=/; Max-Age=0; SameSite=Lax";
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const body = text ? safeJsonParse(text) : null;
  if (!response.ok) {
    if (response.status === 401) {
      clearBrowserAuthState();
      if (typeof window !== "undefined") {
        const path = window.location.pathname;
        if (!path.startsWith("/sign-in") && !path.startsWith("/sign-up")) {
          window.location.href = "/sign-in";
        }
      }
    }
    throw new ApiError(response.status, body);
  }
  return body as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  onboarding_completed: boolean;
  created_at: string;
}

export interface UpdateUserRequest {
  onboarding_completed: boolean;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  description: string | null;
  what_it_does: string | null;
  website_url: string | null;
  owner_id: string;
  meko_datapack_id?: string | null;
  memory_setup_error?: string | null;
  created_at: string;
}

export interface CreateOrganizationRequest {
  name: string;
  description?: string;
  what_it_does?: string;
  website_url?: string;
}

export type UpdateOrganizationRequest = Partial<CreateOrganizationRequest>;

export interface EmployeeResponse {
  id: string;
  org_id: string;
  name: string;
  employee_type: string | null;
  role: string | null;
  personality: Record<string, unknown> | null;
  specialization: string | null;
  duties: unknown[] | null;
  custom_instructions: string | null;
  auto_memory: boolean;
  meko_datapack_id: string | null;
  memory_setup_error: string | null;
  memory_policy: Record<string, unknown> | null;
  escalation_policy: Record<string, unknown> | null;
  mcp_connections: unknown[] | null;
  status: string;
  has_discord_token: boolean;
  has_slack_token: boolean;
  slack_team_name: string | null;
  slack_bot_user_id: string | null;
  channel_assignments: unknown[];
  created_at: string;
  updated_at: string | null;
}

export interface EmployeeMemoryProfileResponse {
  static: string[];
  dynamic: string[];
  search_total: number | null;
  search_timing_ms: number | null;
}

export interface MemorySearchResultResponse {
  provider_result_id: string;
  document_id: string | null;
  container_tag: string;
  score: number | null;
  content: string | null;
  chunks: unknown[];
  metadata: Record<string, unknown>;
  updated_at: string | null;
  version: number | null;
}

export interface MemorySearchResponse {
  query: string;
  tags: string[];
  results: MemorySearchResultResponse[];
  total: number;
}

export interface EmployeeMemoryHistoryEntryResponse {
  id: string;
  memory: string;
  version: number | null;
  created_at: string | null;
  updated_at: string | null;
  parent_memory_id: string | null;
  root_memory_id: string | null;
  is_latest: boolean;
  is_forgotten: boolean;
}

export interface EmployeeMemoryEntryResponse {
  id: string;
  memory: string;
  version: number | null;
  is_latest: boolean;
  is_forgotten: boolean;
  is_static: boolean;
  is_inference: boolean | null;
  created_at: string | null;
  updated_at: string | null;
  space_id: string | null;
  org_id: string | null;
  source_count: number | null;
  parent_memory_id: string | null;
  root_memory_id: string | null;
  forget_after: string | null;
  forget_reason: string | null;
  metadata: Record<string, unknown> | null;
  memory_relations: Record<string, string> | null;
  temporal_context: Record<string, unknown> | null;
  history: EmployeeMemoryHistoryEntryResponse[];
  document_ids: string[];
}

export interface EmployeeMemoryExplorerResponse {
  memory_entries: EmployeeMemoryEntryResponse[];
  current_page: number;
  total_items: number;
  total_pages: number;
  limit: number | null;
}

export interface CreateEmployeeRequest {
  custom_instructions?: string;
  auto_memory?: boolean;
  name: string;
  employee_type: string;
  role?: string;
  personality?: Record<string, unknown>;
  specialization?: string;
  duties?: string[];
  memory_policy?: Record<string, unknown>;
  escalation_policy?: Record<string, unknown>;
}

export interface UpdateEmployeeRequest {
  custom_instructions?: string;
  auto_memory?: boolean;
  name?: string;
  employee_type?: string;
  role?: string;
  personality?: Record<string, unknown>;
  specialization?: string;
  duties?: string[];
  memory_policy?: Record<string, unknown>;
  escalation_policy?: Record<string, unknown>;
  status?: string;
}

export interface ActivityEventResponse {
  id: string;
  event_type: string;
  summary: string;
  description: string | null;
  employee_id: string | null;
  employee_name: string | null;
  platform: string | null;
  status: string | null;
  metadata: Record<string, unknown> | null;
  occurred_at: string;
}

export interface ActivityFeedResponse {
  events: ActivityEventResponse[];
  total: number;
  next_offset: number | null;
}

export interface ActivityStatsResponse {
  total_today: number;
  agent_runs: number;
  source_ingests: number;
  employee_events: number;
  tool_usages: number;
  human_escalations: number;
  memory_operations: number;
}

export interface McpConnectionRead {
  id: string;
  connector_slug: string;
  auth_type: string;
  scopes: string[] | null;
  status: string;
  created_at: string;
}

export interface McpConnectionList {
  connections: McpConnectionRead[];
}

export interface McpConnectionCreate {
  credential: string;
  auth_type?: string;
  server_url?: string;
  scopes?: string[];
  org_wide?: boolean;
}

export interface McpConnector {
  slug: string;
  name: string;
  description: string;
  auth_type: string;
  auth_types: string[];
  requires_custom_server_url: boolean;
  is_connected?: boolean;
}

export interface DocumentResponse {
  id: string;
  org_id: string;
  employee_id: string | null;
  filename: string;
  content_type: string | null;
  size_bytes: number | null;
  status: string;
  error_message: string | null;
  uploaded_at: string;
  source_type: string;
  source_url: string | null;
}

export interface MemorySourceResponse {
  id: string;
  org_id: string;
  employee_id: string | null;
  source_type: string;
  scope: string;
  title: string | null;
  content_text: string | null;
  source_url: string | null;
  provider_memory_id: string | null;
  status: string;
  error_message: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CreateTextMemorySourceRequest {
  scope: "org" | "employee";
  employee_id?: string;
  title?: string;
  content_text: string;
}

export interface CreateUrlMemorySourceRequest {
  scope: "org" | "employee";
  employee_id?: string;
  title?: string;
  source_url: string;
}

export const getOrganizationsGetOrganizationQueryKey = (orgId: string) =>
  ["/api/organizations", orgId] as const;
export const getEmployeesListEmployeesRouteQueryKey = (orgId: string) =>
  ["/api/organizations", orgId, "employees"] as const;
export const getEmployeesGetEmployeeRouteQueryKey = (orgId: string, empId: string) =>
  ["/api/organizations", orgId, "employees", empId] as const;
export const getEmployeesGetMemoryProfileRouteQueryKey = (orgId: string, empId: string) =>
  ["/api/organizations", orgId, "employees", empId, "memory-profile"] as const;
export const getEmployeesGetMemoriesRouteQueryKey = (
  orgId: string,
  empId: string,
  page = 1,
  limit = 25,
) =>
  ["/api/organizations", orgId, "employees", empId, "memories", page, limit] as const;
export const getMemorySearchQueryKey = (
  orgId: string,
  employeeId: string,
  query: string,
) => ["/api/organizations", orgId, "memory", "search", employeeId, query] as const;
export const getMcpListEmployeeMcpConnectionsQueryKey = (orgId: string, empId: string) =>
  ["/api/organizations", orgId, "employees", empId, "mcp-connections"] as const;
export const getMemorySourcesQueryKey = (orgId: string, employeeId?: string) =>
  ["/api/organizations", orgId, "memory-sources", employeeId ?? "org"] as const;
export const getDocumentsListOrgDocumentsQueryKey = ({
  organization_id,
  employee_id,
}: {
  organization_id: string;
  employee_id?: string;
}) => ["/api/documents", organization_id, employee_id ?? "org"] as const;

export function useOrganizationsListOrganizations(
  options?: QueryOptions<OrganizationResponse[]>,
): UseQueryResult<OrganizationResponse[], Error> {
  return useQuery({
    queryKey: ["/api/organizations"],
    queryFn: () => apiRequest<OrganizationResponse[]>("/api/organizations"),
    enabled: options?.query?.enabled,
  });
}

export function useOrganizationsGetOrganization(
  orgId: string,
  options?: QueryOptions<OrganizationResponse>,
): UseQueryResult<OrganizationResponse, Error> {
  return useQuery({
    queryKey: getOrganizationsGetOrganizationQueryKey(orgId),
    queryFn: () => apiRequest<OrganizationResponse>(`/api/organizations/${orgId}`),
    enabled: options?.query?.enabled,
  });
}

export function useOrganizationsCreateOrganization(): UseMutationResult<
  OrganizationResponse,
  Error,
  { data: CreateOrganizationRequest }
> {
  return useMutation({
    mutationFn: ({ data }) =>
      apiRequest<OrganizationResponse>("/api/organizations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useOrganizationsUpdateOrganization(): UseMutationResult<
  OrganizationResponse,
  Error,
  { orgId: string; data: UpdateOrganizationRequest }
> {
  return useMutation({
    mutationFn: ({ orgId, data }) =>
      apiRequest<OrganizationResponse>(`/api/organizations/${orgId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  });
}

export function useOrganizationsDeleteOrganization(): UseMutationResult<
  void,
  Error,
  { orgId: string }
> {
  return useMutation({
    mutationFn: ({ orgId }) =>
      apiRequest<void>(`/api/organizations/${orgId}`, {
        method: "DELETE",
      }),
  });
}

export function useEmployeesListEmployeesRoute(
  orgId: string,
  options?: QueryOptions<EmployeeResponse[]>,
): UseQueryResult<EmployeeResponse[], Error> {
  return useQuery({
    queryKey: getEmployeesListEmployeesRouteQueryKey(orgId),
    queryFn: () => apiRequest<EmployeeResponse[]>(`/api/organizations/${orgId}/employees`),
    enabled: options?.query?.enabled,
  });
}

export function useEmployeesGetEmployeeRoute(
  orgId: string,
  empId: string,
  options?: QueryOptions<EmployeeResponse>,
): UseQueryResult<EmployeeResponse, Error> {
  return useQuery({
    queryKey: getEmployeesGetEmployeeRouteQueryKey(orgId, empId),
    queryFn: () => apiRequest<EmployeeResponse>(`/api/organizations/${orgId}/employees/${empId}`),
    enabled: options?.query?.enabled,
  });
}

export function useEmployeesGetMemoryProfileRoute(
  orgId: string,
  empId: string,
  options?: QueryOptions<EmployeeMemoryProfileResponse>,
): UseQueryResult<EmployeeMemoryProfileResponse, Error> {
  return useQuery({
    queryKey: getEmployeesGetMemoryProfileRouteQueryKey(orgId, empId),
    queryFn: () =>
      apiRequest<EmployeeMemoryProfileResponse>(
        `/api/organizations/${orgId}/employees/${empId}/memory-profile`,
      ),
    enabled: options?.query?.enabled,
  });
}

export function useEmployeesGetMemoriesRoute(
  orgId: string,
  empId: string,
  params?: { page?: number; limit?: number; query?: string },
  options?: QueryOptions<MemoryPage>,
): UseQueryResult<MemoryPage, Error> {
  const page = params?.page ?? 1;
  const limit = params?.limit ?? 25;
  const query = params?.query?.trim() ?? "";
  return useQuery({
    queryKey: [...getEmployeesGetMemoriesRouteQueryKey(orgId, empId, page, limit), query],
    queryFn: () =>
      apiRequest<MemoryPage>(
        `/api/organizations/${orgId}/employees/${empId}/memories?page=${page}&limit=${limit}${query ? `&q=${encodeURIComponent(query)}` : ""}`,
      ),
    enabled: options?.query?.enabled,
    retry: options?.query?.retry,
    refetchInterval: options?.query?.refetchInterval,
  });
}

export function useMemorySearch(
  orgId: string,
  params: { query: string; employee_id: string; limit?: number },
  options?: QueryOptions<MemorySearchResponse>,
): UseQueryResult<MemorySearchResponse, Error> {
  const limit = params.limit ?? 50;
  return useQuery({
    queryKey: getMemorySearchQueryKey(orgId, params.employee_id, params.query),
    queryFn: () =>
      apiRequest<MemorySearchResponse>(`/api/organizations/${orgId}/memory/search`, {
        method: "POST",
        body: JSON.stringify({
          query: params.query,
          employee_id: params.employee_id,
          limit,
          only_matching_chunks: true,
        }),
      }),
    enabled: options?.query?.enabled,
  });
}

export function useEmployeesCreateEmployeeRoute(): UseMutationResult<
  EmployeeResponse,
  Error,
  { orgId: string; data: CreateEmployeeRequest }
> {
  return useMutation({
    mutationFn: ({ orgId, data }) =>
      apiRequest<EmployeeResponse>(`/api/organizations/${orgId}/employees`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useEmployeesUpdateEmployeeRoute(): UseMutationResult<
  EmployeeResponse,
  Error,
  { orgId: string; empId: string; data: UpdateEmployeeRequest }
> {
  return useMutation({
    mutationFn: ({ orgId, empId, data }) =>
      apiRequest<EmployeeResponse>(`/api/organizations/${orgId}/employees/${empId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  });
}

export function useEmployeesDeleteEmployeeRoute(): UseMutationResult<
  void,
  Error,
  { orgId: string; empId: string }
> {
  return useMutation({
    mutationFn: ({ orgId, empId }) =>
      apiRequest<void>(`/api/organizations/${orgId}/employees/${empId}`, {
        method: "DELETE",
      }),
  });
}

export function useEmployeesSetStatus(): UseMutationResult<
  EmployeeResponse,
  Error,
  { orgId: string; empId: string; data: { status: string } }
> {
  return useMutation({
    mutationFn: ({ orgId, empId, data }) =>
      apiRequest<EmployeeResponse>(`/api/organizations/${orgId}/employees/${empId}/status`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  });
}

export function useAuthUpdateMe(): UseMutationResult<
  UserResponse,
  Error,
  { data: UpdateUserRequest }
> {
  return useMutation({
    mutationFn: ({ data }) =>
      apiRequest<UserResponse>("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  });
}

export function useMcpListMcpConnectors(
  orgId: string,
  options?: QueryOptions<McpConnector[]>,
): UseQueryResult<McpConnector[], Error> {
  return useQuery({
    queryKey: [`/api/organizations/${orgId}/mcp-connectors`],
    queryFn: () => apiRequest<McpConnector[]>(`/api/organizations/${orgId}/mcp-connectors`),
    enabled: options?.query?.enabled,
  });
}

export function useMcpListEmployeeMcpConnections(
  orgId: string,
  empId: string,
  options?: QueryOptions<McpConnectionList>,
): UseQueryResult<McpConnectionList, Error> {
  return useQuery({
    queryKey: getMcpListEmployeeMcpConnectionsQueryKey(orgId, empId),
    queryFn: () =>
      apiRequest<McpConnectionList>(`/api/organizations/${orgId}/employees/${empId}/mcp-connections`),
    enabled: options?.query?.enabled,
  });
}

export function useMcpCreateMcpConnection(): UseMutationResult<
  McpConnectionRead,
  Error,
  { orgId: string; empId: string; slug: string; data: McpConnectionCreate }
> {
  return useMutation({
    mutationFn: ({ orgId, empId, slug, data }) =>
      apiRequest<McpConnectionRead>(
        `/api/organizations/${orgId}/employees/${empId}/mcp-connections/${slug}`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      ),
  });
}

export function useMcpDeleteMcpConnection(): UseMutationResult<
  void,
  Error,
  { orgId: string; empId: string; slug: string }
> {
  return useMutation({
    mutationFn: ({ orgId, empId, slug }) =>
      apiRequest<void>(
        `/api/organizations/${orgId}/employees/${empId}/mcp-connections/${slug}`,
        {
          method: "DELETE",
        },
      ),
  });
}

export function useDocumentsListOrgDocuments(
  params: { organization_id: string; employee_id?: string },
  options?: QueryOptions<DocumentResponse[]>,
): UseQueryResult<DocumentResponse[], Error> {
  return useQuery({
    queryKey: getDocumentsListOrgDocumentsQueryKey(params),
    queryFn: () => {
      const search = new URLSearchParams({ organization_id: params.organization_id });
      if (params.employee_id) search.set("employee_id", params.employee_id);
      return apiRequest<DocumentResponse[]>(`/api/documents?${search.toString()}`);
    },
    enabled: options?.query?.enabled,
    refetchInterval: options?.query?.refetchInterval,
  });
}

export function useDocumentsUploadDocument(): UseMutationResult<
  DocumentResponse,
  Error,
  { data: { file: unknown; organization_id: string; employee_id?: string } }
> {
  return useMutation({
    mutationFn: async ({ data }) => {
      const formData = new FormData();
      formData.set("organization_id", data.organization_id);
      if (data.employee_id) formData.set("employee_id", data.employee_id);
      formData.set("file", data.file as Blob);
      return apiRequest<DocumentResponse>("/api/documents", {
        method: "POST",
        body: formData,
      });
    },
  });
}

export function useDocumentsDeleteDocumentRoute(): UseMutationResult<
  void,
  Error,
  { docId: string; organization_id?: string }
> {
  return useMutation({
    mutationFn: ({ docId, organization_id }) => {
      const search = new URLSearchParams();
      if (organization_id) search.set("organization_id", organization_id);
      const suffix = search.toString() ? `?${search.toString()}` : "";
      return apiRequest<void>(`/api/documents/${docId}${suffix}`, {
        method: "DELETE",
      });
    },
  });
}

export function useMemorySourcesList(
  orgId: string,
  employeeId?: string,
  options?: QueryOptions<MemorySourceResponse[]>,
): UseQueryResult<MemorySourceResponse[], Error> {
  return useQuery({
    queryKey: getMemorySourcesQueryKey(orgId, employeeId),
    queryFn: () => {
      const search = employeeId ? `?employee_id=${encodeURIComponent(employeeId)}` : "";
      return apiRequest<MemorySourceResponse[]>(`/api/organizations/${orgId}/memory-sources${search}`);
    },
    enabled: options?.query?.enabled,
    retry: options?.query?.retry,
    refetchInterval: options?.query?.refetchInterval,
  });
}

export function useMemorySourcesCreateText(): UseMutationResult<
  MemorySourceResponse,
  Error,
  { orgId: string; data: CreateTextMemorySourceRequest }
> {
  return useMutation({
    mutationFn: ({ orgId, data }) =>
      apiRequest<MemorySourceResponse>(`/api/organizations/${orgId}/memory-sources/text`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useMemorySourcesCreateUrl(): UseMutationResult<
  MemorySourceResponse,
  Error,
  { orgId: string; data: CreateUrlMemorySourceRequest }
> {
  return useMutation({
    mutationFn: ({ orgId, data }) =>
      apiRequest<MemorySourceResponse>(`/api/organizations/${orgId}/memory-sources/url`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });
}

export function useMemorySourcesDelete(): UseMutationResult<
  void,
  Error,
  { orgId: string; sourceId: string }
> {
  return useMutation({
    mutationFn: ({ orgId, sourceId }) =>
      apiRequest<void>(`/api/organizations/${orgId}/memory-sources/${sourceId}`, {
        method: "DELETE",
      }),
  });
}

export function useMemorySourcesRetry(): UseMutationResult<
  MemorySourceResponse,
  Error,
  { orgId: string; sourceId: string }
> {
  return useMutation({
    mutationFn: ({ orgId, sourceId }) =>
      apiRequest<MemorySourceResponse>(`/api/organizations/${orgId}/memory-sources/${sourceId}/retry`, {
        method: "POST",
      }),
  });
}


export interface MemoryFact {
  updated_at?: string;
  id: string;
  data?: string;
  memory?: string;
  agent_id?: string;
  created_at?: string;
}

export interface MemoryPage {
  memories: MemoryFact[];
  page: number;
  total: number;
  total_pages: number;
}

export interface AgentRun {
  id: string;
  input: string;
  output: string | null;
  platform: string;
  thread_key: string;
  recalled: MemorySearchResultResponse[];
  tools: {name: string; arguments: Record<string, unknown>; status: string; result?: string}[];
  status: string;
  delivery_status: string;
  capture_status: string;
  error: string | null;
  meko_conversation_id: string | null;
  created_at: string;
}

export async function startSlackInstall(orgId: string, employeeId: string): Promise<void> {
  const result = await apiRequest<{authorize_url: string}>("/api/slack/install", {
    method: "POST", body: JSON.stringify({org_id: orgId, employee_id: employeeId}),
  });
  window.location.assign(result.authorize_url);
}
