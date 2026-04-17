"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { label: "Dashboard", href: "/" },
  { section: "CRM" },
  { label: "Customers", href: "/crm/customer" },
  { label: "Opportunities", href: "/crm/opportunity" },
  { label: "Pipelines", href: "/crm/pipeline" },
  { section: "Base" },
  { label: "Companies", href: "/base/company" },
  { label: "Users", href: "/base/user" },
  { label: "Partners", href: "/base/partner" },
  { section: "Technical" },
  { label: "Models", href: "/base/ir-model" },
  { label: "Access", href: "/base/ir-model-access" },
  { label: "Rules", href: "/base/ir-rule" },
  { label: "Parameters", href: "/base/ir-config-param" },
  { label: "Sequences", href: "/base/ir-sequence" },
  { label: "Cron Jobs", href: "/base/ir-cron" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside style={{
      width: 220, background: "#1a1a2e", color: "#e9ecef",
      display: "flex", flexDirection: "column", flexShrink: 0,
    }}>
      <div style={{ padding: "20px 16px", borderBottom: "1px solid #2d2d4e" }}>
        <span style={{ fontWeight: 700, fontSize: 18 }}>Orbiteus</span>
      </div>
      <nav style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {nav.map((item, i) =>
          "section" in item ? (
            <div key={i} style={{
              padding: "12px 16px 4px", fontSize: 11, fontWeight: 700,
              color: "#6c757d", textTransform: "uppercase", letterSpacing: 1,
            }}>
              {item.section}
            </div>
          ) : (
            <Link key={i} href={item.href!} style={{
              display: "block", padding: "8px 16px", fontSize: 14,
              color: path === item.href ? "var(--mantine-color-blue-7)" : "var(--mantine-color-gray-6)",
              background: path === item.href ? "#2d2d4e" : "transparent",
              borderRadius: 4, margin: "1px 8px",
            }}>
              {item.label}
            </Link>
          )
        )}
      </nav>
    </aside>
  );
}
