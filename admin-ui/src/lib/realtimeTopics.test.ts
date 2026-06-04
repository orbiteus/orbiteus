import { describe, expect, it } from "vitest";

import {
  buildSubscribeUrl,
  listTopic,
  resourceToModel,
  shouldClaimLeadership,
  unionTopicSets,
} from "./realtimeTopics";

describe("resourceToModel", () => {
  it("converts module/resource into dotted model name", () => {
    expect(resourceToModel("crm/person")).toBe("crm.person");
    expect(resourceToModel("base/registry-model")).toBe("base.registry-model");
  });

  it("returns the input unchanged when there is no slash", () => {
    expect(resourceToModel("plain")).toBe("plain");
  });
});

describe("buildSubscribeUrl", () => {
  it("encodes multiple topics on one SSE URL", () => {
    const tenant = "550e8400-e29b-41d4-a716-446655440000";
    const url = buildSubscribeUrl([
      listTopic(tenant, "crm.person"),
      listTopic(tenant, "crm.lead"),
    ]);
    expect(url).toContain("topic=tenant%3A");
    expect(url).toContain("crm.person");
    expect(url).toContain("crm.lead");
    expect(url.match(/topic=/g)?.length).toBe(2);
  });

  it("returns empty string when there are no topics", () => {
    expect(buildSubscribeUrl([])).toBe("");
  });
});

describe("unionTopicSets", () => {
  it("deduplicates topics across tabs", () => {
    const union = unionTopicSets([
      new Set(["a", "b"]),
      new Set(["b", "c"]),
    ]);
    expect(union).toEqual(["a", "b", "c"]);
  });
});

describe("shouldClaimLeadership", () => {
  it("claims when there is no leader or the lease is stale", () => {
    expect(shouldClaimLeadership(null, "tab-1", 10_000, 5_000)).toBe(true);
    expect(
      shouldClaimLeadership({ tabId: "other", ts: 1_000 }, "tab-1", 10_000, 5_000),
    ).toBe(true);
  });

  it("keeps leadership for the active tab", () => {
    expect(
      shouldClaimLeadership({ tabId: "tab-1", ts: 9_000 }, "tab-1", 10_000, 5_000),
    ).toBe(true);
    expect(
      shouldClaimLeadership({ tabId: "tab-2", ts: 9_000 }, "tab-1", 10_000, 5_000),
    ).toBe(false);
  });
});
