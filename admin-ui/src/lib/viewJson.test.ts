import { describe, expect, it } from "vitest";
import {
  parseJsonFormLayout,
  parseJsonListView,
  parseJsonKanbanView,
  resolveKanbanGroupField,
} from "./viewJson";

describe("viewJson", () => {
  it("parses list view columns", () => {
    const cols = parseJsonListView({
      model: "crm.lead",
      type: "list",
      columns: [
        { key: "name", label: "Lead" },
        { key: "stage_id", widget: "many2one" },
      ],
    });
    expect(cols).toHaveLength(2);
    expect(cols[0].label).toBe("Lead");
    expect(cols[1].widget).toBe("many2one");
  });

  it("parses form sections layout", () => {
    const layout = parseJsonFormLayout({
      model: "crm.lead",
      type: "form",
      sections: [{ title: "Main", fields: ["name", "stage_id"] }],
    });
    expect(layout?.sections).toHaveLength(1);
    expect(layout?.sections?.[0].fields).toHaveLength(2);
  });

  it("parses kanban view", () => {
    const kb = parseJsonKanbanView({
      model: "crm.lead",
      type: "kanban",
      group_by: "stage_id",
      card_fields: ["name"],
    });
    expect(kb?.group_by).toBe("stage_id");
  });

  it("resolves kanban group field from JSON", () => {
    expect(
      resolveKanbanGroupField({
        model: "crm.lead",
        type: "kanban",
        group_by: "stage_id",
      }),
    ).toBe("stage_id");
  });

  it("rejects invalid list view", () => {
    expect(parseJsonListView({ model: "x", type: "form" })).toEqual([]);
  });
});
