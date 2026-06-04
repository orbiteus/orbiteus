"use client";

import { Badge as MantineBadge, type BadgeProps } from "@mantine/core";

/** Color rules for the canonical CRM (and reasonable defaults). */
const COLOR_BY_VALUE: Record<string, string> = {
  // CRM lead/customer/contact kind
  lead: "cyan",
  customer: "green",
  contact: "gray",
  // Generic statuses
  active: "green",
  inactive: "gray",
  draft: "gray",
  pending: "yellow",
  approved: "green",
  rejected: "red",
  won: "green",
  lost: "red",
  // Audit actor
  user: "blue",
  ai: "violet",
  system: "gray",
};

interface Props extends Omit<BadgeProps, "color"> {
  value: string | null | undefined;
  fallback?: string;
}

export function Badge({ value, fallback = "—", ...rest }: Props) {
  if (value == null || value === "") {
    return <MantineBadge variant="light" color="gray" {...rest}>{fallback}</MantineBadge>;
  }
  const color = COLOR_BY_VALUE[value.toLowerCase()] ?? "gray";
  return <MantineBadge variant="light" color={color} {...rest}>{value}</MantineBadge>;
}
