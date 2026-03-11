import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface QuotaBarProps {
  current: number;
  max: number;
  label?: string;
  className?: string;
}

/**
 * Member quota progress bar.
 * When max is 0, quota is unlimited (shows "Unlimited").
 */
export function QuotaBar({ current, max, label = "Members", className }: QuotaBarProps) {
  const isUnlimited = max === 0;
  const percentage = isUnlimited ? 0 : Math.min((current / max) * 100, 100);
  const isFull = !isUnlimited && current >= max;
  const isNearFull = !isUnlimited && !isFull && percentage >= 80;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span
          className={cn(
            "font-medium",
            isFull && "text-destructive",
            isNearFull && "text-yellow-600",
          )}
        >
          {isUnlimited ? `${current} (Unlimited)` : `${current} / ${max}`}
        </span>
      </div>
      {!isUnlimited && (
        <Progress
          value={percentage}
          className={cn(
            "h-2",
            isFull && "[&>div]:bg-destructive",
            isNearFull && "[&>div]:bg-yellow-500",
          )}
        />
      )}
    </div>
  );
}
