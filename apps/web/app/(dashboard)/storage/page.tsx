"use client";

import { Database } from "lucide-react";
import { useOrganizationsGetOrganization } from "@openhuman/api-client";
import { useOrgStore } from "@/stores/org";
import { Spinner } from "@/components/ui/spinner";
import { SourceManager } from "@/components/source-manager";

export default function StoragePage() {
  const orgId = useOrgStore((s) => s.orgId);
  const { data: org } = useOrganizationsGetOrganization(orgId ?? "", {
    query: { enabled: !!orgId },
  });

  if (!orgId) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-6 py-6">
      <div className="flex items-center gap-2.5">
        <Database className="size-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold tracking-tight text-foreground">
          Knowledge Sources
        </h1>
      </div>
      <div className="mx-auto w-full max-w-3xl">
        <SourceManager
          orgId={orgId}
          title="Workspace knowledge"
          description="Browse company and employee documents."
          orgLabel={org?.name ?? "Company DB"}
          allowDatasetSelection
        />
      </div>
    </div>
  );
}
