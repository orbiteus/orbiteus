"use client";
import { Badge } from "@mantine/core";

const STATUS_COLORS: Record<string, string> = {
  lead: "gray",
  prospect: "blue",
  customer: "green",
  churned: "red",
  inactive: "gray",
  draft: "gray",
  qualified: "blue",
  proposal: "violet",
  won: "green",
  lost: "red",
  active: "green",
  paused: "yellow",
  done: "teal",
  cancelled: "red",
};

export function StatusBadge({ value }: { value: string }) {
  const v = (value || "").toLowerCase();
  const color = STATUS_COLORS[v] ?? "gray";
  return (
    <Badge size="sm" variant="light" color={color} tt="capitalize">
      {value || "—"}
    </Badge>
  );
}
