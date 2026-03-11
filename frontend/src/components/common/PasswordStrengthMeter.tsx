"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface PasswordStrengthMeterProps {
  password: string;
}

interface Criterion {
  label: string;
  met: boolean;
}

function getPasswordCriteria(password: string): Criterion[] {
  return [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "Contains uppercase letter", met: /[A-Z]/.test(password) },
    { label: "Contains lowercase letter", met: /[a-z]/.test(password) },
    { label: "Contains a number", met: /\d/.test(password) },
    { label: "Contains special character", met: /[^a-zA-Z0-9]/.test(password) },
  ];
}

function getStrength(criteria: Criterion[]): {
  score: number;
  label: string;
  color: string;
} {
  const metCount = criteria.filter((c) => c.met).length;

  if (metCount <= 2) return { score: metCount, label: "Weak", color: "bg-red-500" };
  if (metCount <= 3) return { score: metCount, label: "Fair", color: "bg-yellow-500" };
  if (metCount <= 4) return { score: metCount, label: "Good", color: "bg-blue-500" };
  return { score: metCount, label: "Strong", color: "bg-green-500" };
}

export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  const criteria = useMemo(() => getPasswordCriteria(password), [password]);
  const strength = useMemo(() => getStrength(criteria), [criteria]);

  if (!password) return null;

  const widthPercent = (strength.score / criteria.length) * 100;

  return (
    <div className="space-y-2">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full transition-all duration-300", strength.color)}
            style={{ width: `${widthPercent}%` }}
          />
        </div>
        <span
          className={cn(
            "text-xs font-medium",
            strength.score <= 2 && "text-red-500",
            strength.score === 3 && "text-yellow-600",
            strength.score === 4 && "text-blue-500",
            strength.score === 5 && "text-green-600",
          )}
        >
          {strength.label}
        </span>
      </div>

      {/* Criteria checklist */}
      <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {criteria.map((criterion) => (
          <li key={criterion.label} className="flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                "inline-block size-1.5 rounded-full",
                criterion.met ? "bg-green-500" : "bg-muted-foreground/30",
              )}
            />
            <span className={cn(criterion.met ? "text-foreground" : "text-muted-foreground")}>
              {criterion.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
