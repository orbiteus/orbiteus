import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient } from "@tanstack/react-query";

const invalidateQueries = vi.fn();

vi.mock("./queryClient", () => ({
  getQueryClient: () =>
    ({
      invalidateQueries,
      getQueryData: () => undefined,
    }) as unknown as QueryClient,
}));

describe("invalidateModuleRuntimeCaches", () => {
  beforeEach(() => {
    invalidateQueries.mockClear();
  });

  it("invalidates ui-config, i18n, resource, and attachments", async () => {
    const { invalidateModuleRuntimeCaches } = await import("./moduleRuntime");
    invalidateModuleRuntimeCaches();
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["ui-config"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["i18n"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["resource"] });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["attachments"] });
  });
});
