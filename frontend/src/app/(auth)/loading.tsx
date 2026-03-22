import { Skeleton } from "@/components/ui/skeleton";

export default function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Skeleton className="h-80 w-full max-w-md rounded-xl" />
    </div>
  );
}
