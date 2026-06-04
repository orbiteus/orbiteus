import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

/**
 * Logic-level test: we render the component and inspect the
 * resulting React element's props instead of asking happy-dom for a
 * full Mantine portal render. The Badge from `@mantine/core` is
 * thin enough that this is the right level of detail.
 */

function renderProps(value: string) {
  // StatusBadge is a server-rendering-friendly functional component
  // that returns a single <Badge> element. We invoke it directly and
  // read off the resulting `props.color` / `props.children`.
  const node = StatusBadge({ value }) as {
    props: { color: string; children: unknown };
  };
  return node.props;
}

describe("StatusBadge — DoD §9.4 colour contract", () => {
  it("maps known statuses to their canonical colour", () => {
    expect(renderProps("lead").color).toBe("cyan");
    expect(renderProps("won").color).toBe("green");
    expect(renderProps("lost").color).toBe("red");
    expect(renderProps("draft").color).toBe("gray");
    expect(renderProps("active").color).toBe("green");
  });

  it("is case-insensitive on the input value", () => {
    expect(renderProps("WON").color).toBe("green");
    expect(renderProps("Lost").color).toBe("red");
  });

  it("falls back to gray on an unknown status", () => {
    expect(renderProps("zzz_not_a_status").color).toBe("gray");
  });

  it("renders an em-dash when value is empty", () => {
    expect(renderProps("").children).toBe("—");
  });

  it("renders the raw value as the badge label otherwise", () => {
    expect(renderProps("Won").children).toBe("Won");
  });
});
