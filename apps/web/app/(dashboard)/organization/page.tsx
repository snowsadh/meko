"use client";

import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import {
  Building2Icon,
  Trash2Icon,
} from "lucide-react";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  useOrganizationsGetOrganization,
  useOrganizationsUpdateOrganization,
  useOrganizationsDeleteOrganization,
  getOrganizationsGetOrganizationQueryKey,
  ApiError,
} from "@openhuman/api-client";
import { useOrgStore } from "@/stores/org";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { SourceManager } from "@/components/source-manager";
import { MemoryConnection } from "@/components/memory-connection";
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

interface OrgFormData {
  name: string;
  description: string;
  what_it_does: string;
}

export default function OrganizationPage() {
  const orgId = useOrgStore((s) => s.orgId);
  const clearOrg = useOrgStore((s) => s.clearOrg);
  const router = useRouter();
  const queryClient = useQueryClient();
  const updateMutation = useOrganizationsUpdateOrganization();
  const deleteMutation = useOrganizationsDeleteOrganization();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const {
    data: org,
    isLoading: orgLoading,
    isError: orgError,
  } = useOrganizationsGetOrganization(orgId!, {
    query: { enabled: !!orgId },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<OrgFormData>({
    defaultValues: {
      name: "",
      description: "",
      what_it_does: "",
    },
  });

  useEffect(() => {
    if (org) {
      reset({
        name: org.name,
        description: org.description ?? "",
        what_it_does: org.what_it_does ?? "",
      });
    }
  }, [org, reset]);

  const onSubmit = async (data: OrgFormData) => {
    try {
      await updateMutation.mutateAsync({
        orgId: orgId!,
        data: {
          name: data.name,
          description: data.description || undefined,
          what_it_does: data.what_it_does || undefined,
        },
      });
      toast.success("Organization updated");
      queryClient.invalidateQueries({
        queryKey: getOrganizationsGetOrganizationQueryKey(orgId!),
      });
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.messageText || "Failed to update organization");
      } else {
        toast.error("Failed to update organization. Please try again.");
      }
    }
  };

  const handleDelete = useCallback(async () => {
    try {
      await deleteMutation.mutateAsync({ orgId: orgId! });
      clearOrg();
      toast.success("Organization deleted");
      router.push("/setup");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.messageText || "Failed to delete organization");
      } else {
        toast.error("Failed to delete organization. Please try again.");
      }
    }
  }, [deleteMutation, orgId, clearOrg, router]);

  if (!orgId) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (orgLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (orgError || !org) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Building2Icon className="size-10 text-muted-foreground/40" />
        <p className="mt-3 text-sm text-muted-foreground">
          Failed to load organization.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-6 py-6">
      <div className="flex items-center gap-2.5">
        <Building2Icon className="size-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold tracking-tight text-foreground">
          Organization
        </h1>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="mx-auto w-full max-w-2xl space-y-5"
      >
        <div className="space-y-1.5">
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            {...register("name", {
              required: "Name is required",
              minLength: {
                value: 2,
                message: "Name must be at least 2 characters",
              },
            })}
          />
          {errors.name && (
            <p className="text-sm text-destructive">{errors.name.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" rows={3} {...register("description")} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="what_it_does">What does your company do?</Label>
          <Textarea id="what_it_does" rows={3} {...register("what_it_does")} />
        </div>

        <p className="text-xs text-muted-foreground">
          Created {format(new Date(org.created_at), "MMMM d, yyyy")}
        </p>

        <Button
          type="submit"
          size="lg"
          disabled={!isDirty || updateMutation.isPending}
        >
          {updateMutation.isPending ? "Saving..." : "Save changes"}
        </Button>
      </form>

      <Separator className="mx-auto max-w-2xl" />

      <div className="mx-auto w-full max-w-2xl space-y-4">
        <MemoryConnection orgId={orgId!} connected={!!org?.meko_datapack_id} error={org?.memory_setup_error} onConnected={() => void queryClient.invalidateQueries({queryKey:getOrganizationsGetOrganizationQueryKey(orgId!)})} />
        <SourceManager
          orgId={orgId!}
          title="Knowledge Sources"
          description="Add shared company documents."
          orgLabel={org.name}
          targetLabel={org.name}
        />
      </div>

      <Separator className="mx-auto max-w-2xl" />

      <div className="mx-auto w-full max-w-2xl space-y-4">
        <div className="flex items-center gap-2">
          <Trash2Icon className="size-4 text-destructive" />
          <h2 className="text-sm font-semibold text-destructive">
            Danger Zone
          </h2>
        </div>

        <div className="rounded-lg border border-destructive/30 p-4">
          <p className="text-sm text-foreground">
            Permanently delete this organization and all associated data. This
            action cannot be undone.
          </p>
          <Button
            variant="destructive"
            size="sm"
            className="mt-3"
            onClick={() => setDeleteDialogOpen(true)}
          >
            Delete organization
          </Button>
        </div>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete organization?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{" "}
              <span className="font-medium text-foreground">{org.name}</span>{" "}
              and all of its data. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
