import { describe, expect, it } from "vitest";
import { pickPrimaryColumn, secondaryColumns } from "./listLayout";

describe("listLayout", () => {
  const columns = [
    { key: "status", label: "Status" },
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "value", label: "Value" },
  ];

  it("prefers name-like fields as the card title", () => {
    expect(pickPrimaryColumn(columns)?.key).toBe("name");
  });

  it("keeps secondary fields excluding the primary", () => {
    expect(secondaryColumns(columns, "name").map((c) => c.key)).toEqual([
      "status",
      "email",
      "value",
    ]);
  });
});
