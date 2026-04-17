"use client";

import { Breadcrumbs, Anchor } from "@mantine/core";
import Link from "next/link";
import { usePathname } from "next/navigation";

function humanize(segment: string): string {
  return segment
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Dashboard / Module / Model / … from URL path */
export default function PageBreadcrumbs() {
  const path = usePathname();
  if (!path || path === "/" || path === "/login") return null;

  const segments = path.split("/").filter(Boolean);
  if (segments.length === 0) return null;

  const items: { label: string; href: string }[] = [{ label: "Dashboard", href: "/" }];

  let acc = "";
  for (let i = 0; i < segments.length; i++) {
    acc += `/${segments[i]}`;
    const seg = segments[i];
    const isUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg);
    const label = isUuid ? "Record" : humanize(seg);
    items.push({ label, href: acc });
  }

  return (
    <Breadcrumbs mb="md" separator="›" style={{ flexWrap: "wrap" }}>
      {items.map((it, idx) =>
        idx === items.length - 1 ? (
          <span key={it.href} style={{ color: "var(--mantine-color-dimmed)", fontSize: 13 }}>
            {it.label}
          </span>
        ) : (
          <Anchor key={it.href} component={Link} href={it.href} size="sm">
            {it.label}
          </Anchor>
        ),
      )}
    </Breadcrumbs>
  );
}
