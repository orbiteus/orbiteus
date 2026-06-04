import { describe, expect, it } from "vitest";
import { queryKeys } from "./queryKeys";

describe("portal queryKeys", () => {
  it("builds stable share view keys", () => {
    expect(queryKeys.shareView("abc")).toEqual(["portal", "share", "abc"]);
  });
});
