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
  Alert,
  Stack,
  Paper,
  SimpleGrid,
  List,
  ThemeIcon,
  Anchor,
  Group,
} from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";

const highlights = [
  "Modułowy rdzeń CRM i ERP — pipeline, role, widoki",
  "RBAC i audyt — bezpieczny dostęp do danych firmy",
  "AI-native: Command Palette i automatyzacje pod Twój stack",
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
      <Box
        p={{ base: "xl", md: 48 }}
        style={{
          background:
            "linear-gradient(145deg, #0b1220 0%, #151b2e 42%, #1a2744 100%)",
          color: "#f1f5f9",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <Text size="xs" tt="uppercase" fw={700} c="cyan.3" mb="sm" style={{ letterSpacing: "0.12em" }}>
          Orbiteus · demo
        </Text>
        <Title order={1} fz={{ base: 28, sm: 34 }} fw={800} lh={1.15} mb="md">
          Composable CRM &amp; ERP — fundament pod produkt i usługi
        </Title>
        <Text size="md" c="gray.4" maw={520} mb="xl" lh={1.6}>
          To środowisko demonstracyjne Orbiteusa: ten sam stack co w repozytorium, z pełnym API i panelem
          administracyjnym. Zaloguj się, żeby zobaczyć pipeline, role i moduły w akcji — podobnie jak w
          inspiracji z{" "}
          <Anchor href="https://demo.openmercato.com" target="_blank" rel="noreferrer" c="cyan.3">
            Open Mercato
          </Anchor>
          , ale w naszej architekturze i brandingu.
        </Text>
        <List
          spacing="sm"
          size="sm"
          center
          icon={
            <ThemeIcon color="cyan" variant="light" radius="xl" size={28}>
              <IconCircleCheck size={16} />
            </ThemeIcon>
          }
        >
          {highlights.map((line) => (
            <List.Item key={line} c="gray.2">
              {line}
            </List.Item>
          ))}
        </List>
        <Text size="xs" c="gray.6" mt="xl">
          Produkcja i pełna dokumentacja:{" "}
          <Anchor href="https://orbiteus.com" c="gray.5" target="_blank" rel="noreferrer">
            orbiteus.com
          </Anchor>
        </Text>
      </Box>

      <Box
        p={{ base: "lg", md: 48 }}
        style={{
          background: "var(--mantine-color-gray-0)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Paper p="xl" radius="md" w="100%" maw={420} withBorder shadow="sm">
          <Stack gap="lg">
            <Box>
              <Group gap="sm" mb="xs">
                {branding.logo_url ? (
                  <img src={branding.logo_url} alt={branding.name} style={{ height: 40 }} />
                ) : (
                  <Title order={2}>{branding.name}</Title>
                )}
              </Group>
              <Text c="dimmed" size="sm">
                Zaloguj się do panelu administracyjnego
              </Text>
            </Box>

            {error && (
              <Alert icon={<IconAlertCircle size={16} />} color="red">
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <Stack gap="sm">
                <TextInput
                  label="E-mail"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
                <PasswordInput
                  label="Hasło"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <Button type="submit" loading={loading} fullWidth mt="sm" size="md">
                  Zaloguj
                </Button>
              </Stack>
            </form>

            <Text size="xs" c="dimmed" ta="center">
              Pierwsze konto tworzy się przy starcie backendu zgodnie z konfiguracją serwera — użyj
              danych od administratora demo lub hasła ustawionego w zmiennych środowiskowych.
            </Text>
          </Stack>
        </Paper>
      </Box>
    </SimpleGrid>
  );
}
