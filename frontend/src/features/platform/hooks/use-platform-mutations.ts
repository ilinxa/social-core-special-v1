import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  updatePlatformProfileApi,
  type UpdatePlatformProfileData,
} from "@/features/platform/api/platform-api";
import { queryKeys } from "@/lib/query-keys";

export function useUpdatePlatformProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdatePlatformProfileData) => updatePlatformProfileApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.platform.account() });
    },
  });
}
