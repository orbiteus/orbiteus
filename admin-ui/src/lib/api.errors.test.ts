import { describe, expect, it } from "vitest";
import axios from "axios";
import { extractApiError, isUserFacingApiDetailSafe } from "./api";

describe("isUserFacingApiDetailSafe", () => {
  it("rejects HTML error pages", () => {
    expect(isUserFacingApiDetailSafe("<!doctype html><html>")).toBe(false);
  });

  it("accepts short backend detail", () => {
    expect(isUserFacingApiDetailSafe("Record not found")).toBe(true);
  });
});

describe("extractApiError", () => {
  it("returns safe detail from axios response", () => {
    const err = new axios.AxiosError(
      "Request failed",
      "ERR",
      undefined,
      undefined,
      {
        status: 404,
        data: { detail: "Not found" },
        statusText: "Not Found",
        headers: {},
        config: {} as never,
      },
    );
    expect(extractApiError(err, "Fallback")).toBe("Not found");
  });

  it("falls back when detail is HTML", () => {
    const err = new axios.AxiosError(
      "Request failed",
      "ERR",
      undefined,
      undefined,
      {
        status: 502,
        data: "<html>Bad Gateway</html>",
        statusText: "Bad Gateway",
        headers: {},
        config: {} as never,
      },
    );
    expect(extractApiError(err, "Action failed")).toBe("Action failed");
  });
});
