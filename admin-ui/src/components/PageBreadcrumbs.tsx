"use client";

import { Breadcrumbs, Anchor, Text } from "@mantine/core";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { humanizeRegistrySlugForUi } from "@/lib/formatters";
import { useT } from "@orbiteus/i18n";

/** Dashboard / Module / Model / … from URL path */
export default function PageBreadcrumbs() {
  const t = useT();
  const path = usePathname();
  if (!path || path === "/" || path === "/login") return null;

  const segments = path.split("/").filter(Boolean);
  if (segments.length === 0) return null;

  const items: { label: string; href: string }[] = [{ label: t("breadcrumb.dashboard"), href: "/" }];

  let acc = "";
  for (let i = 0; i < segments.length; i++) {
    acc += `/${segments[i]}`;
    const seg = segments[i];
    const isUuid =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg);
    const label = isUuid ? t("breadcrumb.record") : humanizeRegistrySlugForUi(seg);
    items.push({ label, href: acc });
  }

  return (
    <Breadcrumbs mb="sm" separator="/" style={{ flexWrap: "wrap" }}>
      {items.map((it, idx) =>
        idx === items.length - 1 ? (
          <Text key={it.href} size="sm" c="dimmed" component="span">
            {it.label}
          </Text>
        ) : (
          <Anchor key={it.href} component={Link} href={it.href} size="sm">
            {it.label}
          </Anchor>
        ),
      )}
    </Breadcrumbs>
  );
}
