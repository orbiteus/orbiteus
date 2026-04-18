"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Title,
  Text,
  TextInput,
  PasswordInput,
  Button,
  Stack,
  Paper,
  SimpleGrid,
  List,
  Anchor,
  Group,
} from "@mantine/core";
import { IconCircleCheck } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";

const highlights = [
  "Modular CRM & ERP core — pipelines, roles, and configurable views",
  "RBAC and audit-ready access patterns for your organization data",
  "AI-native command palette and automation hooks on your stack",
];

const mono = {
  black: "#0a0a0a",
  white: "#fafafa",
  mutedOnDark: "#a3a3a3",
  mutedOnLight: "#525252",
} as const;

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
      <Box
        p={{ base: "xl", md: 48 }}
        style={{
          background: mono.black,
          color: mono.white,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          borderRight: "1px solid #262626",
        }}
      >
        <Text
          size="xs"
          tt="uppercase"
          fw={700}
          mb="sm"
          style={{ letterSpacing: "0.14em", color: mono.mutedOnDark }}
        >
          Orbiteus · demo
        </Text>
        <Title order={1} fz={{ base: 28, sm: 34 }} fw={700} lh={1.15} mb="md" c={mono.white}>
          Composable CRM &amp; ERP for product and service companies
        </Title>
        <Text size="md" maw={520} mb="xl" lh={1.65} style={{ color: mono.mutedOnDark }}>
          This is a live Orbiteus demo: the same stack as the repository, with the full API and admin UI.
          Sign in to explore pipelines, roles, and modules — layout inspired by{" "}
          <Anchor
            href="https://demo.openmercato.com"
            target="_blank"
            rel="noreferrer"
            c={mono.white}
            underline="always"
            style={{ fontWeight: 600 }}
          >
            Open Mercato
          </Anchor>
          , adapted to our architecture and monochrome design system.
        </Text>
        <List
          spacing="sm"
          size="sm"
          center
          icon={
            <Box
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                border: `1px solid ${mono.mutedOnDark}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: mono.white,
              }}
            >
              <IconCircleCheck size={14} stroke={1.5} />
            </Box>
          }
        >
          {highlights.map((line) => (
            <List.Item key={line} style={{ color: mono.white }}>
              {line}
            </List.Item>
          ))}
        </List>
        <Text size="xs" mt="xl" style={{ color: "#737373" }}>
          Production site and docs:{" "}
          <Anchor href="https://orbiteus.com" c={mono.white} underline="always" target="_blank" rel="noreferrer">
            orbiteus.com
          </Anchor>
        </Text>
      </Box>

      <Box
        p={{ base: "lg", md: 48 }}
        style={{
          background: mono.white,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Paper
          p="xl"
          radius={0}
          w="100%"
          maw={420}
          withBorder
          styles={{
            root: {
              borderColor: mono.black,
              borderWidth: 1,
              boxShadow: "none",
            },
          }}
        >
          <Stack gap="lg">
            <Box>
              <Group gap="sm" mb="xs">
                {branding.logo_url ? (
                  <img src={branding.logo_url} alt={branding.name} style={{ height: 40 }} />
                ) : (
                  <Title order={2} c={mono.black}>
                    {branding.name}
                  </Title>
                )}
              </Group>
              <Text size="sm" style={{ color: mono.mutedOnLight }}>
                Sign in to the admin console
              </Text>
            </Box>

            {error ? (
              <Box
                p="sm"
                style={{
                  border: `1px solid ${mono.black}`,
                  background: "#f5f5f5",
                  color: mono.black,
                  fontSize: "var(--mantine-font-size-sm)",
                }}
              >
                {error}
              </Box>
            ) : null}

            <form onSubmit={handleSubmit}>
              <Stack gap="sm">
                <TextInput
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  styles={{
                    label: { color: mono.black, fontWeight: 600 },
                    input: {
                      borderRadius: 0,
                      borderColor: mono.black,
                      color: mono.black,
                    },
                  }}
                />
                <PasswordInput
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  styles={{
                    label: { color: mono.black, fontWeight: 600 },
                    input: {
                      borderRadius: 0,
                      borderColor: mono.black,
                      color: mono.black,
                    },
                  }}
                />
                <Button
                  type="submit"
                  loading={loading}
                  fullWidth
                  mt="sm"
                  size="md"
                  radius={0}
                  styles={{
                    root: {
                      backgroundColor: mono.black,
                      color: mono.white,
                      border: `1px solid ${mono.black}`,
                      "&:hover": { backgroundColor: "#262626" },
                    },
                  }}
                >
                  Sign in
                </Button>
              </Stack>
            </form>

            <Text size="xs" ta="center" style={{ color: mono.mutedOnLight }}>
              The first admin account is created on backend startup from server configuration — use credentials
              from your demo operator or the bootstrap values set in environment variables.
            </Text>
          </Stack>
        </Paper>
      </Box>
    </SimpleGrid>
  );
}
