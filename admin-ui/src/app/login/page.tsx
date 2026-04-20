"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Center, Box, Title, Text, TextInput, PasswordInput,
  Button, Alert, Stack, Paper,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";

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
    <Center h="100vh" style={{ background: "var(--mantine-color-gray-1)" }}>
      <Paper p="xl" radius="md" w={380} withBorder>
        <Stack gap="lg">
          <Box>
            {branding.logo_url
              ? <img src={branding.logo_url} alt={branding.name} style={{ height: 36, marginBottom: 8 }} />
              : <Title order={2}>{branding.name}</Title>
            }
            <Text c="dimmed" size="sm">Sign in to your account</Text>
          </Box>

          {error && (
            <Alert icon={<IconAlertCircle size={16} />} color="red">
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <TextInput
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
              <PasswordInput
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Button type="submit" loading={loading} fullWidth mt="sm">
                Sign in
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
    </Center>
  );
}
