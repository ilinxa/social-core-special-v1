import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: (failureCount, error) => {
          if (failureCount >= 3) return false;
          if (
            error instanceof ApiError &&
            [400, 401, 403, 404, 409, 422].includes(error.status)
          ) {
            return false;
          }
          return true;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
