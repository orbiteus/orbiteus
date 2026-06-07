import { describe, expect, it } from "vitest";
import { FRONTEND_STACK_VERSIONS } from "./frontendStackVersions";

describe("FRONTEND_STACK_VERSIONS", () => {
  it("exposes semver strings for frontend tiles", () => {
    expect(FRONTEND_STACK_VERSIONS.adminUi).toMatch(/^\d+\.\d+\.\d+/);
    expect(FRONTEND_STACK_VERSIONS.i18n).toMatch(/^\d+\.\d+\.\d+/);
    expect(FRONTEND_STACK_VERSIONS.next).toBeTruthy();
    expect(FRONTEND_STACK_VERSIONS.reactQuery).toBeTruthy();
  });
});
