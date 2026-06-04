"use client";
/**
 * Settings → Mail
 *
 * Configure the default outbound SMTP relay for transactional mail
 * (password reset, notifications, etc.). Settings persist in
 * ``base_config_params`` and override environment defaults once saved.
 *
 * Backend:
 *   GET  /api/base/mail/settings
 *   PUT  /api/base/mail/settings
 *   POST /api/base/mail/settings/test-connection
 *   POST /api/base/mail/settings/send-test
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  NumberInput,
  Paper,
  PasswordInput,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconMail,
  IconPlugConnected,
  IconSend,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface MailSettings {
  source: "environment" | "database";
  configured: boolean;
  host: string;
  port: number;
  user: string;
  use_tls: boolean;
  from_address: string;
  has_password: boolean;
}

function apiDetail(err: unknown, fallback: string): string {
  if (err && typeof err === "object" && "response" in err) {
    const data = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof data === "string") return data;
    if (data && typeof data === "object" && "message" in data) {
      return String((data as { message: unknown }).message);
    }
  }
  return fallback;
}

export default function MailSettingsPage() {
  const t = useT();
  const { user, hydrated } = useAuth();

  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<MailSettings["source"]>("environment");
  const [configured, setConfigured] = useState(false);
  const [hasPassword, setHasPassword] = useState(false);

  const [host, setHost] = useState("");
  const [port, setPort] = useState<number | "">(587);
  const [smtpUser, setSmtpUser] = useState("");
  const [password, setPassword] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [fromAddress, setFromAddress] = useState("");

  const [testEmail, setTestEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [formError, setFormError] = useState("");

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setFormError("");
    try {
      const { data } = await api.get<MailSettings>("/base/mail/settings", {
        skipGlobalErrorToast: true,
      });
      setSource(data.source);
      setConfigured(data.configured);
      setHasPassword(data.has_password);
      setHost(data.host ?? "");
      setPort(data.port ?? 587);
      setSmtpUser(data.user ?? "");
      setUseTls(data.use_tls ?? true);
      setFromAddress(data.from_address ?? "");
      if (user?.email) setTestEmail(user.email);
    } catch (e) {
      setFormError(apiDetail(e, t("mail.errorLoad")));
    } finally {
      setLoading(false);
    }
  }, [user?.email]);

  useEffect(() => {
    if (hydrated) void loadSettings();
  }, [hydrated, loadSettings]);

  function smtpPayload(includePassword: boolean) {
    return {
      host: host.trim(),
      port: typeof port === "number" ? port : 587,
      user: smtpUser.trim(),
      use_tls: useTls,
      from_address: fromAddress.trim(),
      ...(includePassword && password ? { password } : {}),
    };
  }

  async function handleSave() {
    setSaving(true);
    setFormError("");
    try {
      const { data } = await api.put<MailSettings>("/base/mail/settings", {
        ...smtpPayload(true),
        password: password || undefined,
      });
      setSource(data.source);
      setConfigured(data.configured);
      setHasPassword(data.has_password);
      setPassword("");
      notifications.show({
        title: t("mail.savedTitle"),
        message: t("mail.savedMessage"),
        color: "green",
        icon: <IconCheck size={16} />,
      });
    } catch (e) {
      setFormError(apiDetail(e, t("mail.errorSave")));
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    setTestingConn(true);
    setFormError("");
    try {
      await api.post("/base/mail/settings/test-connection", smtpPayload(true), {
        skipGlobalErrorToast: true,
      });
      notifications.show({
        title: t("mail.connectionOkTitle"),
        message: t("mail.connectionOkMessage"),
        color: "green",
        icon: <IconCheck size={16} />,
      });
    } catch (e) {
      setFormError(apiDetail(e, t("mail.connectionTestFailed")));
    } finally {
      setTestingConn(false);
    }
  }

  async function handleSendTest() {
    if (!testEmail.trim()) {
      setFormError(t("mail.enterRecipient"));
      return;
    }
    setSendingTest(true);
    setFormError("");
    try {
      await api.post(
        "/base/mail/settings/send-test",
        { ...smtpPayload(true), to: testEmail.trim() },
        { skipGlobalErrorToast: true },
      );
      notifications.show({
        title: t("mail.testSentTitle"),
        message: t("mail.testSentMessage", { email: testEmail.trim() }),
        color: "green",
        icon: <IconCheck size={16} />,
      });
    } catch (e) {
      setFormError(apiDetail(e, t("mail.testSendFailed")));
    } finally {
      setSendingTest(false);
    }
  }

  if (!hydrated || loading) {
    return (
      <Stack align="center" py="xl">
        <Loader color="gray" />
      </Stack>
    );
  }

  if (!user?.is_superadmin) {
    return (
      <Alert color="orange" title={t("mail.superadminRequiredTitle")} icon={<IconAlertCircle size={16} />}>
        {t("mail.superadminRequiredBody")}
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <Group gap="sm">
        <IconMail size={28} stroke={1.5} />
        <Stack gap={2}>
          <Title order={2}>{t("nav.settings.mail")}</Title>
          <Text c="dimmed" size="sm">
            {t("mail.description")}
          </Text>
        </Stack>
      </Group>

      <Group gap="xs">
        <Badge variant="light" color={configured ? "green" : "gray"}>
          {configured ? t("mail.configuredInDb") : t("mail.notSavedYet")}
        </Badge>
        <Badge variant="light" color="cyan">
          {t("mail.activeSource")}: {source === "database" ? t("mail.sourceAdmin") : t("mail.sourceEnv")}
        </Badge>
        {hasPassword ? (
          <Badge variant="light" color="teal">{t("mail.passwordStored")}</Badge>
        ) : null}
      </Group>

      {formError ? (
        <Alert color="red" title={t("common.error")} icon={<IconAlertCircle size={16} />}>
          {formError}
        </Alert>
      ) : null}

      <Paper withBorder p="md">
        <Stack gap="md">
          <Text fw={600} size="sm">{t("mail.smtpServer")}</Text>
          <Group grow align="flex-start">
            <TextInput
              label={t("mail.host")}
              placeholder="smtp.example.com"
              required
              value={host}
              onChange={(e) => setHost(e.currentTarget.value)}
            />
            <NumberInput
              label={t("mail.port")}
              min={1}
              max={65535}
              value={port}
              onChange={(v) => setPort(typeof v === "number" ? v : "")}
            />
          </Group>
          <Group grow align="flex-start">
            <TextInput
              label={t("mail.username")}
              placeholder={t("mail.optional")}
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.currentTarget.value)}
            />
            <PasswordInput
              label={t("auth.password")}
              placeholder={hasPassword ? t("mail.passwordKeepCurrent") : t("mail.optional")}
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
            />
          </Group>
          <TextInput
            label={t("mail.fromAddress")}
            placeholder="no-reply@yourcompany.com"
            value={fromAddress}
            onChange={(e) => setFromAddress(e.currentTarget.value)}
          />
          <Switch
            label={t("mail.useStartTls")}
            checked={useTls}
            onChange={(e) => setUseTls(e.currentTarget.checked)}
          />
          <Group>
            <Button loading={saving} onClick={() => void handleSave()}>
              {t("mail.saveSettings")}
            </Button>
            <Button
              variant="light"
              leftSection={<IconPlugConnected size={16} />}
              loading={testingConn}
              onClick={() => void handleTestConnection()}
            >
              {t("mail.testConnection")}
            </Button>
          </Group>
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Stack gap="md">
          <Text fw={600} size="sm">{t("mail.sendTestEmail")}</Text>
          <Text size="sm" c="dimmed">
            {t("mail.sendTestHint")}
          </Text>
          <Group align="flex-end">
            <TextInput
              label={t("mail.recipient")}
              placeholder="you@example.com"
              value={testEmail}
              onChange={(e) => setTestEmail(e.currentTarget.value)}
              style={{ flex: 1 }}
            />
            <Button
              leftSection={<IconSend size={16} />}
              loading={sendingTest}
              onClick={() => void handleSendTest()}
            >
              {t("mail.sendTest")}
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Stack>
  );
}
