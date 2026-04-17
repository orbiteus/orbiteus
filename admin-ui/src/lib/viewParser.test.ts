import { describe, expect, it } from "vitest";
import { parseCalendarView, parseGraphView } from "./viewParser";

describe("parseGraphView", () => {
  it("reads row and measure fields from graph arch", () => {
    const arch = `
      <graph type="bar">
        <field name="stage_id" type="row"/>
        <field name="expected_revenue" type="measure"/>
      </graph>`;
    expect(parseGraphView(arch)).toEqual({
      rowField: "stage_id",
      measureField: "expected_revenue",
      type: "bar",
    });
  });

  it("returns null when measure is missing", () => {
    const arch = `<graph><field name="x" type="row"/></graph>`;
    expect(parseGraphView(arch)).toBeNull();
  });
});

describe("parseCalendarView", () => {
  it("reads date_start and defaults", () => {
    const arch = `<calendar date_start="close_date" date_stop="date_deadline" mode="month"/>`;
    expect(parseCalendarView(arch)).toEqual({
      dateStart: "close_date",
      dateStop: "date_deadline",
      mode: "month",
    });
  });
});
