"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import {
  Alert,
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Code,
  Container,
  Flex,
  Group,
  List,
  Loader,
  Paper,
  PasswordInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconApi,
  IconArrowLeft,
  IconBook,
  IconBrandGithub,
  IconCircleCheck,
  IconDatabase,
  IconShieldLock,
  IconUsers,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";
import { loginNeedsTotpStep } from "@/lib/loginTotp";
import { PublicNavLink } from "@/components/PublicNavLink";

const WELCOME_LS_KEY = "orbiteus_show_welcome";

/** Baked at `next build` — public demo hosts pass these as Docker build args. */
const DEMO_EMAIL_PUBLIC = process.env.NEXT_PUBLIC_DEMO_LOGIN_EMAIL ?? "";
const DEMO_PASSWORD_PUBLIC = process.env.NEXT_PUBLIC_DEMO_LOGIN_PASSWORD ?? "";

const README_LOCAL_EMAIL = "admin@example.com";
const README_LOCAL_PASSWORD = "admin1234";

type HealthJson = { status?: string; service?: string };
type UiModule = { name: string; label: string; models: { name: string }[] };

type AuthStep = "welcome" | "signin";

const fluidPx = { base: "md", sm: "xl", lg: "3rem", xl: "4rem" } as const;

export default function LoginPage() {
  const t = useT();
  const roleCards: {
    title: string;
    blurb: string;
    features: string[];
    icon: typeof IconShieldLock;
    cta: string;
  }[] = [
    {
      title: t("login.card.superadmin.title"),
      blurb: t("login.card.superadmin.blurb"),
      features: [
        t("login.card.superadmin.feature1"),
        t("login.card.superadmin.feature2"),
        t("login.card.superadmin.feature3"),
        t("login.card.superadmin.feature4"),
      ],
      icon: IconShieldLock,
      cta: t("login.card.superadmin.cta"),
    },
    {
      title: t("login.card.ops.title"),
      blurb: t("login.card.ops.blurb"),
      features: [
        t("login.card.ops.feature1"),
        t("login.card.ops.feature2"),
        t("login.card.ops.feature3"),
        t("login.card.ops.feature4"),
      ],
      icon: IconUsers,
      cta: t("login.card.ops.cta"),
    },
    {
      title: t("login.card.integration.title"),
      blurb: t("login.card.integration.blurb"),
      features: [
        t("login.card.integration.feature1"),
        t("login.card.integration.feature2"),
        t("login.card.integration.feature3"),
        t("login.card.integration.feature4"),
      ],
      icon: IconApi,
      cta: t("login.card.integration.cta"),
    },
  ];
  const branding = useBranding();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState("");

  // DoD §9.9 — `/login` is now sign-in only. The welcome page lives at
  // `/welcome`. We keep `fullWelcome` as state so the legacy
  // localStorage flag still works as an opt-in (developers who liked
  // the embedded welcome can flip it back), but the default is FALSE
  // so a clean visitor lands directly on the form.
  const [fullWelcome, setFullWelcome] = useState(false);
  const [welcomeChecked, setWelcomeChecked] = useState(false);
  const [authStep, setAuthStep] = useState<AuthStep>("signin");

  const [health, setHealth] = useState<HealthJson | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const [modules, setModules] = useState<UiModule[]>([]);
  const [metaLoading, setMetaLoading] = useState(false);

  // SSR renders the relative "/api" string; the client swaps in the absolute
  // URL after hydration to avoid a Next.js text mismatch warning.
  const [apiBase, setApiBase] = useState<string>("/api");
  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiBase(`${window.location.origin}/api`);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Legacy: if a developer pre-flipped `WELCOME_LS_KEY=true` we honour
    // it, otherwise the default is "form only" (the welcome content
    // lives at /welcome from now on).
    const v = localStorage.getItem(WELCOME_LS_KEY);
    const show = v === "true";
    setFullWelcome(show);
    setWelcomeChecked(show);
    if (show) setAuthStep("welcome");
  }, []);

  const saveWelcomePreference = useCallback((checked: boolean) => {
    localStorage.setItem(WELCOME_LS_KEY, checked ? "true" : "false");
    setWelcomeChecked(checked);
  }, []);

  const applyPublicDemoPrefill = useCallback(() => {
    setTotpRequired(false);
    setTotpCode("");
    if (DEMO_EMAIL_PUBLIC) setEmail(DEMO_EMAIL_PUBLIC);
    else setEmail(README_LOCAL_EMAIL);
    if (DEMO_PASSWORD_PUBLIC) setPassword(DEMO_PASSWORD_PUBLIC);
    else setPassword(README_LOCAL_PASSWORD);
  }, []);

  const goToSignIn = useCallback(() => {
    setAuthStep("signin");
    setError("");
    applyPublicDemoPrefill();
  }, [applyPublicDemoPrefill]);

  const goToWelcome = useCallback(() => {
    setAuthStep("welcome");
    setPassword("");
    setError("");
    setTotpRequired(false);
    setTotpCode("");
  }, []);

  useEffect(() => {
    if (authStep !== "welcome") return;
    let cancelled = false;
    (async () => {
      setMetaLoading(true);
      try {
        const h = await fetch("/api/base/health");
        if (!h.ok) throw new Error("bad");
        const hj = (await h.json()) as HealthJson;
        if (!cancelled) {
          setHealth(hj);
          setHealthErr(false);
        }
      } catch {
        if (!cancelled) {
          setHealth(null);
          setHealthErr(true);
        }
      }
      try {
        const u = await fetch("/api/base/ui-config");
        if (u.ok) {
          const j = (await u.json()) as { modules?: UiModule[] };
          if (!cancelled && Array.isArray(j.modules)) setModules(j.modules);
        }
      } catch {
        /* optional */
      } finally {
        if (!cancelled) setMetaLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authStep]);

  useEffect(() => {
    if (!fullWelcome) applyPublicDemoPrefill();
  }, [fullWelcome, applyPublicDemoPrefill]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Backend sets `orbiteus_token` httpOnly cookie in the Set-Cookie header
      // (see docs/adr/0017). The body still includes `access_token` for
      // non-browser clients but we no longer write it to localStorage.
      const body: { email: string; password: string; totp_code?: string } = { email, password };
      if (totpRequired) {
        body.totp_code = totpCode.trim();
      }
      const { data } = await api.post("/auth/login", body, { skipGlobalErrorToast: true });
      if (loginNeedsTotpStep(data)) {
        setTotpRequired(true);
        setTotpCode("");
        return;
      }
      // Hard navigation forces SSR + middleware to read the fresh cookie.
      const params = new URLSearchParams(window.location.search);
      const next = params.get("next") || "/";
      window.location.assign(next);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && !err.response) {
        setError(
          err.code === "ECONNABORTED"
            ? t("auth.login.timeout")
            : t("auth.login.unreachable"),
        );
      } else {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(typeof msg === "string" ? msg : t("auth.login.failed"));
      }
    } finally {
      setLoading(false);
    }
  }

  // `apiBase` lives in state above to keep SSR and the client in sync.

  const hasBakedDemoCreds = Boolean(DEMO_EMAIL_PUBLIC && DEMO_PASSWORD_PUBLIC);

  const demoCredentialsPanel = (
    <Paper withBorder p="xl" h="100%">
      <Stack gap="md">
        <Title order={4}>{t("auth.login.demoCredentials")}</Title>
        {hasBakedDemoCreds ? (
          <Stack gap="md">
            <Box>
              <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
                {t("auth.email")}
              </Text>
              <Code block>{DEMO_EMAIL_PUBLIC}</Code>
            </Box>
            <Box>
              <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
                {t("auth.password")}
              </Text>
              <Code block>{DEMO_PASSWORD_PUBLIC}</Code>
            </Box>
            <Text size="xs" c="dimmed">
              {t("auth.login.demoShownBecause")}{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_*
              </Text>
              . {t("auth.login.demoRotate")}
            </Text>
          </Stack>
        ) : (
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              {t("auth.login.demoNoSecrets")}
            </Text>
            <Text size="sm" fw={600}>
              {t("auth.login.readmeLocalDocker")}
            </Text>
            <Code block>
              {README_LOCAL_EMAIL}
              {"\n"}
              {README_LOCAL_PASSWORD}
            </Code>
            <Text size="xs" c="dimmed">
              {t("auth.login.demoRebuildPrefix")}{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_EMAIL
              </Text>{" "}
              {t("auth.login.and")}{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_PASSWORD
              </Text>{" "}
              {t("auth.login.demoRebuildSuffix")} <Text span ff="monospace">BOOTSTRAP_ADMIN_*</Text>.
            </Text>
          </Stack>
        )}
      </Stack>
    </Paper>
  );

  const signInFormPanel = (
    <Paper withBorder p="xl" id="sign-in" h="100%">
      <Stack gap="md">
        <Box>
          <Group gap="sm" mb={4}>
            {branding.hydrated && branding.logo_url ? (
              <img src={branding.logo_url} alt={branding.name} style={{ height: 36 }} />
            ) : (
              <Title order={3} c="dark.9">
                {branding.name}
              </Title>
            )}
          </Group>
          <Text size="sm" c="dimmed">
            {t("auth.login.signInWithAccount")}
          </Text>
        </Box>
        {error ? (
          <Alert icon={<IconAlertCircle size={18} />} color="dark" variant="light" title={t("auth.login.signInError")}>
            {error}
          </Alert>
        ) : null}
        <form onSubmit={handleSubmit}>
          <Stack gap="sm">
            <TextInput
              id="sign-in-email"
              label={t("auth.email")}
              type="email"
              value={email}
              onChange={(e) => {
                setTotpRequired(false);
                setTotpCode("");
                setEmail(e.target.value);
              }}
              required
              autoFocus
            />
            <PasswordInput
              label={t("auth.password")}
              value={password}
              onChange={(e) => {
                setTotpRequired(false);
                setTotpCode("");
                setPassword(e.target.value);
              }}
              required
            />
            {totpRequired ? (
              <TextInput
                id="sign-in-totp"
                label={t("auth.login.authenticatorOrRecovery")}
                description={t("auth.login.authenticatorHint")}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                required
                autoComplete="one-time-code"
                inputMode="numeric"
              />
            ) : null}
            <Group justify="flex-end">
              <PublicNavLink size="sm" c="dark" href="/forgot-password">
                {t("auth.login.forgotPassword")}
              </PublicNavLink>
            </Group>
            <Button type="submit" loading={loading} fullWidth mt="xs" size="md" color="dark">
              {t("auth.signIn")}
            </Button>
          </Stack>
        </form>
      </Stack>
    </Paper>
  );

  const signInStepLayout = (opts: { showBack: boolean }) => (
    <Box bg="gray.0" w="100%">
      <Container fluid px={fluidPx} py="xl" w="100%">
        <Stack gap="xl" w="100%">
          {opts.showBack ? (
            <Button
              variant="subtle"
              color="dark"
              leftSection={<IconArrowLeft size={18} />}
              onClick={goToWelcome}
              w="fit-content"
            >
              {t("auth.login.backToWelcome")}
            </Button>
          ) : null}
          <Title order={1} fz={{ base: 28, sm: 34 }}>
            {t("auth.signIn")}
          </Title>
          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl" w="100%">
            {demoCredentialsPanel}
            {signInFormPanel}
          </SimpleGrid>
        </Stack>
      </Container>
    </Box>
  );

  if (!fullWelcome) {
    return (
      <Box bg="gray.0" mih="100vh" w="100%">
        {signInStepLayout({ showBack: false })}
        <Container fluid px={fluidPx} pb="xl">
          <Text ta="center" size="sm">
            <PublicNavLink href="/welcome" c="dark" fw={600}>
              {t("auth.login.showFullWelcome")}
            </PublicNavLink>
          </Text>
        </Container>
      </Box>
    );
  }

  if (authStep === "signin") {
    return (
      <Box bg="gray.0" mih="100vh" w="100%">
        {signInStepLayout({ showBack: true })}
      </Box>
    );
  }

  return (
    <Box bg="gray.0" mih="100vh" pb="xl" w="100%">
      <Container fluid px={fluidPx} pt="md" pb="xl" w="100%" mx={0}>
        <Stack gap="xl" w="100%" align="flex-start">
          <Box
            component="header"
            w="100%"
            pb="md"
            style={{
              borderBottom: "1px solid var(--mantine-color-default-border)",
            }}
          >
            <Flex direction="column" align="flex-start" gap="xs" w="100%" wrap="nowrap">
              <Group gap="sm" justify="flex-start" align="center" wrap="nowrap" w="100%">
                {/* `branding.hydrated` is false during SSR / first paint —
                    this gate keeps the markup identical between the server
                    and client so React doesn't report a hydration mismatch
                    when the logo URL arrives from /api/base/branding. */}
                {branding.hydrated && branding.logo_url ? (
                  <img
                    src={branding.logo_url}
                    alt={branding.name}
                    style={{ height: 44, width: "auto", display: "block" }}
                  />
                ) : (
                  <Title order={2} c="dark.9">
                    {branding.name}
                  </Title>
                )}
              </Group>
              <Text size="sm" c="dimmed" ta="left" maw={{ base: "100%", md: "42rem", lg: "50rem" }} lh={1.55}>
                {t("login.heroTagline")}
              </Text>
            </Flex>
          </Box>

          <Stack gap="md" align="flex-start" w="100%">
            <Title order={1} ta="left" fz={{ base: 26, sm: 34 }} fw={700} w="100%">
              {t("login.welcomeTitle")}
            </Title>
            <Text c="dimmed" ta="left" lh={1.65} w="100%" maw={{ base: "100%", md: "48rem", lg: "56rem" }} size="md">
              {t("login.welcomeIntro")}
            </Text>
          </Stack>

          <Alert color="dark" variant="outline" title={t("login.demoSecurityTitle")}>
            <List spacing="xs" size="sm" mt="xs" withPadding>
              <List.Item>
                {t("login.demoSecurityItem1")}
              </List.Item>
              <List.Item>
                {t("login.demoSecurityItem2Prefix")}{" "}
                <Text span fw={600}>
                  SECRET_KEY
                </Text>{" "}
                {t("login.demoSecurityItem2Suffix")}
              </List.Item>
              <List.Item>
                {t("login.demoSecurityItem3Prefix")}{" "}
                <Anchor href="https://github.com/orbiteus/orbiteus" target="_blank" rel="noreferrer" fw={600}>
                  {t("login.githubReadme")}
                </Anchor>
                .
              </List.Item>
            </List>
          </Alert>

          <Box w="100%">
            <Title order={3} mb="md" ta="center">
              {t("login.chooseDemoUse")}
            </Title>
            <Text c="dimmed" ta="center" mb="lg" size="sm" w="100%">
              {t("login.chooseDemoUseHint")}
            </Text>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md" w="100%">
              {roleCards.map((card) => {
                const RoleIcon = card.icon;
                return (
                  <Card key={card.title} withBorder padding="lg" radius="md" h="100%">
                    <Stack gap="sm" h="100%">
                      <ThemeIcon variant="outline" color="dark" size="lg" radius="md">
                        <RoleIcon size={22} stroke={1.5} />
                      </ThemeIcon>
                      <Title order={4}>{card.title}</Title>
                      <Text size="sm" c="dimmed" lh={1.55}>
                        {card.blurb}
                      </Text>
                      <Text size="xs" fw={700} tt="uppercase" c="dimmed" mt="xs">
                        {t("login.availableInBuild")}
                      </Text>
                      <List
                        spacing={6}
                        size="sm"
                        icon={
                          <ThemeIcon variant="transparent" color="dark" size={20} radius="xl">
                            <IconCircleCheck size={14} stroke={1.5} />
                          </ThemeIcon>
                        }
                        style={{ flex: 1 }}
                      >
                        {card.features.map((f) => (
                          <List.Item key={f}>{f}</List.Item>
                        ))}
                      </List>
                      <Button fullWidth mt="auto" variant="filled" color="dark" onClick={goToSignIn}>
                        {card.cta}
                      </Button>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          </Box>

          <Box w="100%">
            <Title order={3} mb="md">
              {t("login.apiResources")}
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md" w="100%">
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  {t("login.apiCardDocsTitle")}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("login.apiCardDocsDesc")}
                </Text>
                <Anchor href="/api/docs" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  {t("login.apiCardDocsCta")}
                </Anchor>
              </Paper>
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  {t("login.apiCardJsonTitle")}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("login.apiCardJsonDesc")}
                </Text>
                <Anchor href="/api/openapi.json" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  {t("login.apiCardJsonCta")}
                </Anchor>
              </Paper>
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  {t("login.apiCardRepoTitle")}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("login.apiCardRepoDesc")}
                </Text>
                <Anchor
                  href="https://github.com/orbiteus/orbiteus"
                  target="_blank"
                  rel="noreferrer"
                  size="sm"
                  fw={600}
                >
                  <Group gap={6} wrap="nowrap">
                    <IconBrandGithub size={16} /> orbiteus/orbiteus
                  </Group>
                </Anchor>
              </Paper>
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  {t("login.apiCardSiteTitle")}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("login.apiCardSiteDesc")}
                </Text>
                <Anchor href="https://orbiteus.com" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  <Group gap={6} wrap="nowrap">
                    <IconBook size={16} /> orbiteus.com
                  </Group>
                </Anchor>
              </Paper>
            </SimpleGrid>
            <Text size="sm" mt="md" c="dimmed">
              {t("login.currentApiBase")}{" "}
              <Text span ff="monospace" size="sm" c="dark.8">
                {apiBase}
              </Text>
            </Text>
          </Box>

          <Checkbox
            checked={welcomeChecked}
            onChange={(e) => saveWelcomePreference(e.currentTarget.checked)}
            label={t("login.displayWelcomeNextTime")}
            color="dark"
          />

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" w="100%">
            <Paper withBorder p="md">
              <Group gap="sm" mb="sm">
                <ThemeIcon variant="outline" color="dark" size="md" radius="md">
                  <IconDatabase size={18} />
                </ThemeIcon>
                <Title order={4}>{t("login.databaseStatus")}</Title>
              </Group>
              {metaLoading ? (
                <Loader size="sm" color="dark" />
              ) : healthErr ? (
                <Text size="sm" c="dimmed">
                  {t("login.healthUnreachablePrefix")} <Text span ff="monospace">/api/base/health</Text>. {t("login.healthUnreachableSuffix")}
                </Text>
              ) : (
                <Stack gap={4}>
                  <Text size="sm">
                    {t("login.status")}{" "}
                    <Text span fw={700} tt="uppercase">
                      {health?.status ?? t("login.unknown")}
                    </Text>
                  </Text>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {health?.service}
                  </Text>
                </Stack>
              )}
            </Paper>

            <Paper withBorder p="md">
              <Title order={4} mb="sm">
                {t("login.activeModules")}
              </Title>
              {metaLoading && !modules.length ? (
                <Loader size="sm" color="dark" />
              ) : (
                <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="sm" w="100%">
                  {modules.map((m) => (
                    <Paper key={m.name} withBorder p="sm" radius="sm">
                      <Group justify="space-between" wrap="nowrap" gap="xs">
                        <Text size="sm" fw={600} lineClamp={1}>
                          {m.label || m.name}
                        </Text>
                        <Badge size="xs" variant="outline" color="dark" radius="sm">
                          v0.1.0
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed" mt={4}>
                        {t("login.modelsCount", { count: m.models?.length ?? 0 })}
                      </Text>
                    </Paper>
                  ))}
                </SimpleGrid>
              )}
            </Paper>
          </SimpleGrid>

          <Stack gap="xs" align="center" pt="md" w="100%">
            <Group gap="md" justify="center" wrap="wrap">
              <PublicNavLink href="/login" size="sm" c="dark" fw={600}>
                {t("login.footerWelcome")}
              </PublicNavLink>
              <Text size="sm" c="dimmed">
                ·
              </Text>
              <Anchor href="https://github.com/orbiteus/orbiteus/blob/main/README.md" size="sm" c="dark" fw={600}>
                {t("login.footerReadme")}
              </Anchor>
              <Text size="sm" c="dimmed">
                ·
              </Text>
              <Anchor href="/api/docs" size="sm" c="dark" fw={600}>
                {t("login.footerApiDocs")}
              </Anchor>
            </Group>
            <Text size="xs" c="dimmed" ta="center">
              {t("login.footerBuiltWith")}
            </Text>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}
