import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PreferenceRow } from "@/features/notifications/components/PreferenceRow";
import { NOTIFICATION_CATEGORY_LABELS } from "@/features/notifications/constants/notification-constants";
import type { PreferenceItem } from "@/features/notifications/types";

interface PreferenceCategorySectionProps {
  category: string;
  items: PreferenceItem[];
  onToggle: (
    notificationType: string,
    channel: "email" | "push" | "sms",
    enabled: boolean,
  ) => void;
  onReset: (notificationType: string) => void;
}

export function PreferenceCategorySection({
  category,
  items,
  onToggle,
  onReset,
}: PreferenceCategorySectionProps) {
  const label = NOTIFICATION_CATEGORY_LABELS[category] ?? category;

  return (
    <Card>
      <CardHeader className="pb-3">
        <h3 className="text-base font-semibold leading-none">{label}</h3>
      </CardHeader>
      <CardContent>
        {items.map((item, index) => (
          <div key={item.notification_type}>
            {index > 0 && <Separator className="my-1" />}
            <PreferenceRow item={item} onToggle={onToggle} onReset={onReset} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
