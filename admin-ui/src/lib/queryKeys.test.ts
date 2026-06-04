import { describe, expect, it } from "vitest";
import { queryKeys } from "./queryKeys";

describe("queryKeys", () => {
  it("uiConfig key is stable", () => {
    expect(queryKeys.uiConfig()).toEqual(["ui-config"]);
  });

  it("resource detail includes expand segment", () => {
    expect(queryKeys.resourceDetail("crm/lead", "abc", "person_id,stage_id")).toEqual([
      "resource",
      "detail",
      "crm/lead",
      "abc",
      "person_id,stage_id",
    ]);
  });

  it("list key embeds params for cache separation", () => {
    const a = queryKeys.resourceList("crm/lead", { limit: 50, offset: 0 });
    const b = queryKeys.resourceList("crm/lead", { limit: 50, offset: 50 });
    expect(a).not.toEqual(b);
  });

  it("attachments key embeds filter params", () => {
    expect(queryKeys.attachments({ res_model: "base.company", res_id: "x" })).toEqual([
      "attachments",
      "list",
      { res_model: "base.company", res_id: "x" },
    ]);
  });
});
