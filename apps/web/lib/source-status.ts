export function getSourceStatusLabel(status: string): string {
  switch (status) {
    case "indexed":
      return "Ready";
    case "pending":
      return "Syncing";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

export function getSourceStatusClassName(status: string): string {
  switch (status) {
    case "indexed":
      return "border-green-200 bg-green-50 text-green-700";
    case "pending":
      return "border-border bg-secondary text-secondary-foreground";
    case "failed":
      return "border-red-200 bg-red-50 text-red-700";
    default:
      return "";
  }
}
