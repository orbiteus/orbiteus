import { describe, expect, it } from "vitest";

import {
  componentTileColor,
  statusColor,
  statusLabel,
} from "./systemStatus";

describe("systemStatus helpers", () => {
  it("maps probe status to semantic colors", () => {
    expect(statusColor("ok")).toBe("green");
    expect(statusColor("degraded")).toBe("red");
    expect(statusColor("skipped")).toBe("gray");
    expect(statusColor("unknown")).toBe("yellow");
  });

  it("labels status for tiles", () => {
    expect(statusLabel("ok")).toBe("Healthy");
    expect(statusLabel("degraded")).toBe("Degraded");
  });

  it("assigns colorful tile accents by component id", () => {
    expect(componentTileColor("sqlalchemy")).toBe("indigo");
    expect(componentTileColor("ai_module_config")).toBe("pink");
    expect(componentTileColor("missing")).toBe("gray");
  });
});
