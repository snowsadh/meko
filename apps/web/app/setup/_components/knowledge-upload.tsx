"use client";

import { SourceManager } from "@/components/source-manager";
import { Button } from "@/components/ui/button";

interface KnowledgeUploadProps {
  orgId: string;
  onComplete: () => void;
  onSkip: () => void;
}

export function KnowledgeUpload({ orgId, onComplete, onSkip }: KnowledgeUploadProps) {
  return (
    <div className="space-y-6">
      <SourceManager
        orgId={orgId}
        compact
        title="Starter knowledge"
        description="Add either supported documents or URLs now. You can continue refining the company knowledge DB from the dashboard."
      />
      <div className="flex items-center justify-end gap-3">
        <Button variant="ghost" onClick={onSkip}>
          Skip for now
        </Button>
        <Button onClick={onComplete}>Continue to dashboard</Button>
      </div>
    </div>
  );
}
