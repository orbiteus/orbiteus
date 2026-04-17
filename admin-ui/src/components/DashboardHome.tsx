"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  SimpleGrid, Paper, Stack, Title, Text, Group, ThemeIcon, Loader, Alert, Button,
} from "@mantine/core";
import {
  IconUsers, IconBriefcase, IconTrendingUp, IconCash, IconTrophy,
} from "@tabler/icons-react";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";

interface CrmStats {
  total_customers: number;
  total_opportunities: number;
  won_opportunities: number;
  pipeline_value: number;
  won_revenue: number;
}

export default function DashboardHome() {
  const [stats, setStats] = useState<CrmStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<CrmStats>("/crm/stats")
      .then(({ data }) => setStats(data))
      .catch(() => setError("Could not load CRM statistics."));
  }, []);

  if (error) {
    return (
      <Stack gap="md">
        <Title order={3}>Dashboard</Title>
        <Alert color="yellow" title="CRM stats unavailable">{error}</Alert>
        <Text c="dimmed" size="sm">Ensure you are logged in and the CRM module is loaded.</Text>
      </Stack>
    );
  }

  if (!stats) {
    return (
      <Stack gap="md" align="center" py="xl">
        <Loader color="gray" />
        <Text c="dimmed" size="sm">Loading dashboard…</Text>
      </Stack>
    );
  }

  const cards = [
    {
      label: "Customers",
      value: String(stats.total_customers),
      icon: IconUsers,
      color: "blue",
      href: "/crm/customer",
    },
    {
      label: "Open opportunities",
      value: String(stats.total_opportunities),
      icon: IconBriefcase,
      color: "cyan",
      href: "/crm/opportunity",
    },
    {
      label: "Won deals",
      value: String(stats.won_opportunities),
      icon: IconTrophy,
      color: "green",
      href: "/crm/opportunity",
    },
    {
      label: "Pipeline value",
      value: formatMoney(stats.pipeline_value),
      icon: IconTrendingUp,
      color: "grape",
      href: "/crm/opportunity",
    },
    {
      label: "Won revenue",
      value: formatMoney(stats.won_revenue),
      icon: IconCash,
      color: "teal",
      href: "/crm/opportunity",
    },
  ] as const;

  return (
    <Stack gap="lg">
      <div>
        <Title order={3}>Dashboard</Title>
        <Text c="dimmed" size="sm" mt={4}>
          Overview of your CRM — data from <Text span ff="monospace" size="xs">GET /api/crm/stats</Text>
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
        {cards.map((c) => (
          <Paper
            key={c.label}
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
                  {c.label}
                </Text>
                <Text size="xl" fw={700} mt={4}>
                  {c.value}
                </Text>
              </div>
              <ThemeIcon size={44} radius="md" variant="light" color={c.color}>
                <c.icon size={24} stroke={1.5} />
              </ThemeIcon>
            </Group>
          </Paper>
        ))}
      </SimpleGrid>

      <Paper p="md" withBorder radius="md">
        <Text size="sm" fw={600} mb="xs">Quick links</Text>
        <Group gap="sm">
          <Button component={Link} href="/crm/pipeline" variant="default" size="xs">Pipelines</Button>
          <Button component={Link} href="/base/company" variant="default" size="xs">Companies</Button>
          <Button component={Link} href="/base/user" variant="default" size="xs">Users</Button>
        </Group>
      </Paper>
    </Stack>
  );
}
