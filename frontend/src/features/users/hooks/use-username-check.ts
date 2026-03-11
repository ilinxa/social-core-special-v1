import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { checkUsernameApi } from "@/features/users/api/users-api";

export interface UsernameCheckResult {
  isChecking: boolean;
  isAvailable: boolean | null;
  isCurrent: boolean;
}

export function useUsernameCheck(username: string, currentUsername: string): UsernameCheckResult {
  const [debouncedUsername, setDebouncedUsername] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedUsername(username);
    }, 500);
    return () => clearTimeout(timer);
  }, [username]);

  const isFormatValid = /^[a-zA-Z0-9_]{5,30}$/.test(debouncedUsername);
  const isSameAsCurrent = debouncedUsername.toLowerCase() === currentUsername.toLowerCase();
  const shouldCheck = isFormatValid && !isSameAsCurrent && debouncedUsername.length > 0;

  const { data, isFetching } = useQuery({
    queryKey: queryKeys.users.checkUsername(debouncedUsername),
    queryFn: () => checkUsernameApi(debouncedUsername),
    enabled: shouldCheck,
    staleTime: 30 * 1000,
    retry: false,
  });

  if (isSameAsCurrent) {
    return { isChecking: false, isAvailable: true, isCurrent: true };
  }

  if (!shouldCheck) {
    return { isChecking: false, isAvailable: null, isCurrent: false };
  }

  return {
    isChecking: isFetching,
    isAvailable: data?.available ?? null,
    isCurrent: data?.is_current ?? false,
  };
}
