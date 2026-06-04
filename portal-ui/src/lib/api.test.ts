import { describe, expect, it } from "vitest";
import { isUserFacingApiDetailSafe, extractApiError } from "./api";

describe("portal api errors", () => {
  it("rejects HTML error bodies", () => {
    expect(isUserFacingApiDetailSafe("<html>bad</html>")).toBe(false);
  });

  it("extracts Error message", () => {
    expect(extractApiError(new Error("Token expired"), "Fallback")).toBe("Token expired");
  });
});
