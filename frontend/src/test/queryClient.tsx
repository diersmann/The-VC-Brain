/* eslint-disable react-refresh/only-export-components */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

/**
 * Create a QueryClient configured for testing.
 * Disables retries and stale times so tests don't hang.
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
    },
  });
}

/**
 * Wraps children in a QueryClientProvider for testing.
 */
export function TestQueryProvider({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}
