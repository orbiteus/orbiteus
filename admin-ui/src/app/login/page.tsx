"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Anchor,
  Box,
  Button,
  Flex,
  Group,
  List,
  Paper,
  PasswordInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";

const highlights = [
  "Modular CRM & ERP core — pipelines, roles, and configurable views",
  "RBAC and audit-ready access patterns for your organization data",
  "AI-native command palette and automation hooks on your stack",
];

export default function LoginPage() {
  const router = useRouter();
  const branding = useBranding();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("token", data.access_token);
      router.push("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing={0} mih="100vh">
      <Flex
        direction="column"
        justify="center"
        p={{ base: "xl", md: 48 }}
        bg="dark.9"
        c="gray.0"
        style={{ borderRight: "1px solid var(--mantine-color-dark-6)" }}
      >
        <Text size="xs" tt="uppercase" fw={700} mb="sm" c="dimmed" style={{ letterSpacing: "0.14em" }}>
          Orbiteus · demo
        </Text>
        <Title order={1} fz={{ base: 28, sm: 34 }} fw={700} lh={1.15} mb="md" c="gray.0">
          Composable CRM &amp; ERP for product and service companies
        </Title>
        <Text size="md" maw={520} mb="xl" lh={1.65} c="dimmed">
          This is a live Orbiteus demo: the same stack as the repository, with the full API and admin UI.
          Sign in to explore pipelines, roles, and modules — layout inspired by{" "}
          <Anchor href="https://demo.openmercato.com" target="_blank" rel="noreferrer" c="gray.0" fw={600} underline="always">
            Open Mercato
          </Anchor>
          , adapted to our architecture and Mantine-based design system.
        </Text>
        <List
          spacing="sm"
          size="sm"
          center
          icon={
            <ThemeIcon variant="outline" color="gray" radius="xl" size={28} aria-hidden>
              <IconCircleCheck size={14} stroke={1.5} />
            </ThemeIcon>
          }
        >
          {highlights.map((line) => (
            <List.Item key={line} c="gray.1">
              {line}
            </List.Item>
          ))}
        </List>
        <Text size="xs" mt="xl" c="dimmed">
          Production site and docs:{" "}
          <Anchor href="https://orbiteus.com" c="gray.0" underline="always" target="_blank" rel="noreferrer">
            orbiteus.com
          </Anchor>
        </Text>
      </Flex>

      <Flex p={{ base: "lg", md: 48 }} bg="gray.0" align="center" justify="center">
        <Paper p="xl" w="100%" maw={420} withBorder>
          <Stack gap="lg">
            <Box>
              <Group gap="sm" mb="xs">
                {branding.logo_url ? (
                  <img src={branding.logo_url} alt={branding.name} style={{ height: 40 }} />
                ) : (
                  <Title order={2} c="dark.9">
                    {branding.name}
                  </Title>
                )}
              </Group>
              <Text size="sm" c="dimmed">
                Sign in to the admin console
              </Text>
            </Box>

            {error ? (
              <Alert icon={<IconAlertCircle size={18} />} color="dark" variant="light" title="Sign-in error">
                {error}
              </Alert>
            ) : null}

            <form onSubmit={handleSubmit}>
              <Stack gap="sm">
                <TextInput label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
                <PasswordInput label="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                <Button type="submit" loading={loading} fullWidth mt="sm" size="md" color="dark">
                  Sign in
                </Button>
              </Stack>
            </form>

            <Text size="xs" c="dimmed" ta="center">
              The first admin account is created on backend startup from server configuration — use credentials
              from your demo operator or the bootstrap values set in environment variables.
            </Text>
          </Stack>
        </Paper>
      </Flex>
    </SimpleGrid>
  );
}
