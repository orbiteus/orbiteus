"use client";

import { useState } from "react";
import {
  Anchor,
  Box,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useT } from "@orbiteus/i18n";
import { api } from "@/lib/api";

/**
 * Public password-reset request page (DoD §3.4).
 *
 * The endpoint always returns 200 — we therefore always show the same
 * confirmation copy, regardless of whether the email exists, to avoid
 * leaking enumeration data through the UI.
 */
export default function ForgotPasswordPage() {
  const t = useT();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/password/request", { email });
      setSubmitted(true);
    } catch (err: unknown) {
      // Even on transient failure we keep the same message.
      setSubmitted(true);
      if (err instanceof Error) {
        console.warn("password.request.transient_error", err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box bg="gray.0" mih="100vh" w="100%">
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack gap="md">
            <Title order={2}>{t("auth.forgot.title")}</Title>
            {submitted ? (
              <Stack gap="sm">
                <Text>
                  {t("auth.forgot.successBody")}
                </Text>
                <Text size="sm" c="dimmed">
                  {t("auth.forgot.successHint")}
                </Text>
                <Group>
                  <Anchor href="/login" size="sm">
                    {t("auth.forgot.backToSignIn")}
                  </Anchor>
                </Group>
              </Stack>
            ) : (
              <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                  <Text>
                    {t("auth.forgot.intro")}
                  </Text>
                  <TextInput
                    label={t("auth.email")}
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                  />
                  {error ? (
                    <Text c="red" size="sm">
                      {error}
                    </Text>
                  ) : null}
                  <Group justify="space-between" mt="xs">
                    <Anchor href="/login" size="sm" c="dark">
                      {t("auth.forgot.backToSignIn")}
                    </Anchor>
                    <Button type="submit" loading={loading} color="dark">
                      {t("auth.forgot.sendLink")}
                    </Button>
                  </Group>
                </Stack>
              </form>
            )}
          </Stack>
        </Card>
      </Container>
    </Box>
  );
}
