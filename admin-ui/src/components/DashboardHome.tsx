"use client";
import Link from "next/link";
import {
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconBuilding,
  IconSettings,
  IconUsers,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { PromptInput } from "@/orbiteus-ui";

const QUICK_LINKS = [
  { labelKey: "dashboard.link.companies", href: "/base/company", icon: IconBuilding, color: "blue" },
  { labelKey: "dashboard.link.users", href: "/base/user", icon: IconUsers, color: "cyan" },
  { labelKey: "dashboard.link.modules", href: "/modules", icon: IconSettings, color: "gray" },
] as const;

export default function DashboardHome() {
  const t = useT();
  return (
    <Stack gap="lg">
      <div>
        <Title order={3}>{t("nav.dashboard")}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t("dashboard.engineReadyPrefix")}{" "}
          <Text component={Link} href="/modules" span inherit c="blue">
            {t("dashboard.modules")}
          </Text>{" "}
          {t("dashboard.engineReadySuffix")}
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        {QUICK_LINKS.map((c) => (
          <Paper
            key={c.labelKey}
            component={Link}
            href={c.href}
            p="md"
            radius="md"
            withBorder
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.05em" }}>
                  {t(c.labelKey)}
                </Text>
                <Text size="sm" mt={4}>{t("dashboard.open")}</Text>
              </div>
              <ThemeIcon size={44} radius="md" variant="light" color={c.color}>
                <c.icon size={24} stroke={1.5} />
              </ThemeIcon>
            </Group>
          </Paper>
        ))}
      </SimpleGrid>

      <Paper p="md" withBorder radius="md">
        <Text size="sm" fw={600} mb="xs">{t("dashboard.aiSection")}</Text>
        <PromptInput scope="global" placeholder={t("dashboard.askPlaceholder")} />
      </Paper>

      <Paper p="md" withBorder radius="md">
        <Text size="sm" fw={600} mb="xs">{t("dashboard.quickLinks")}</Text>
        <Group gap="sm">
          {QUICK_LINKS.map((c) => (
            <Button key={c.href} component={Link} href={c.href} variant="default" size="xs">
              {t(c.labelKey)}
            </Button>
          ))}
        </Group>
      </Paper>
    </Stack>
  );
}
