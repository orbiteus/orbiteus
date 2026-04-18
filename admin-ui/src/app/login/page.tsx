"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { api } from "@/lib/api";
import { useBranding } from "@/lib/branding";

const WELCOME_LS_KEY = "orbiteus_show_welcome";

/** Baked at `next build` — public demo hosts pass these as Docker build args. */
const DEMO_EMAIL_PUBLIC = process.env.NEXT_PUBLIC_DEMO_LOGIN_EMAIL ?? "";
const DEMO_PASSWORD_PUBLIC = process.env.NEXT_PUBLIC_DEMO_LOGIN_PASSWORD ?? "";

const README_LOCAL_EMAIL = "admin@example.com";
const README_LOCAL_PASSWORD = "admin1234";

type HealthJson = { status?: string; service?: string };
type UiModule = { name: string; label: string; models: { name: string }[] };

type AuthStep = "welcome" | "signin";

const roleCards: {
  title: string;
  blurb: string;
  features: string[];
  icon: typeof IconShieldLock;
  cta: string;
}[] = [
  {
    title: "Super administrator",
    blurb: "Bootstrap account with full technical access — RBAC, system parameters, and CRM configuration.",
    features: [
      "Manage users, roles, and access rules",
      "Technical models, cron jobs, sequences",
      "CRM pipelines, stages, and master data",
      "Branding and instance-wide settings",
    ],
    icon: IconShieldLock,
    cta: "Sign in as super admin",
  },
  {
    title: "Operations & CRM",
    blurb: "Day-to-day revenue work: accounts, opportunities, and pipeline views inside the same demo tenant.",
    features: [
      "Customers, opportunities, and pipelines",
      "List, form, kanban, and calendar perspectives",
      "Fuzzy search and Command Palette (⌘K)",
      "Same JWT session as the admin shell",
    ],
    icon: IconUsers,
    cta: "Sign in to CRM workspace",
  },
  {
    title: "Integrations & API",
    blurb: "Treat Orbiteus as a headless engine — OpenAPI-first, module registry, no vendor UI lock-in.",
    features: [
      "Auto-generated REST + OpenAPI per model",
      "Extend with registry.register(\"your_module\")",
      "PostgreSQL + Alembic migrations at startup",
      "MIT stack: FastAPI, SQLAlchemy, Next.js",
    ],
    icon: IconApi,
    cta: "Sign in for API work",
  },
];

const fluidPx = { base: "md", sm: "xl", lg: "3rem", xl: "4rem" } as const;

export default function LoginPage() {
  const router = useRouter();
  const branding = useBranding();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [fullWelcome, setFullWelcome] = useState(true);
  const [welcomeChecked, setWelcomeChecked] = useState(true);
  const [authStep, setAuthStep] = useState<AuthStep>("welcome");

  const [health, setHealth] = useState<HealthJson | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const [modules, setModules] = useState<UiModule[]>([]);
  const [metaLoading, setMetaLoading] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const v = localStorage.getItem(WELCOME_LS_KEY);
    const show = v !== "false";
    setFullWelcome(show);
    setWelcomeChecked(show);
  }, []);

  const saveWelcomePreference = useCallback((checked: boolean) => {
    localStorage.setItem(WELCOME_LS_KEY, checked ? "true" : "false");
    setWelcomeChecked(checked);
  }, []);

  const applyPublicDemoPrefill = useCallback(() => {
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
  }, []);

  useEffect(() => {
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
  }, []);

  useEffect(() => {
    if (!fullWelcome) applyPublicDemoPrefill();
  }, [fullWelcome, applyPublicDemoPrefill]);

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

  const apiBase =
    typeof window !== "undefined" ? `${window.location.origin}/api` : "/api";

  const hasBakedDemoCreds = Boolean(DEMO_EMAIL_PUBLIC && DEMO_PASSWORD_PUBLIC);

  const demoCredentialsPanel = (
    <Paper withBorder p="xl" h="100%">
      <Stack gap="md">
        <Title order={4}>Demo credentials</Title>
        {hasBakedDemoCreds ? (
          <Stack gap="md">
            <Box>
              <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
                Email
              </Text>
              <Code block>{DEMO_EMAIL_PUBLIC}</Code>
            </Box>
            <Box>
              <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
                Password
              </Text>
              <Code block>{DEMO_PASSWORD_PUBLIC}</Code>
            </Box>
            <Text size="xs" c="dimmed">
              Shown because this image was built with{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_*
              </Text>
              . Rotate after evaluation.
            </Text>
          </Stack>
        ) : (
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              This build does not ship operator-specific secrets. Use the defaults from the README for a local Docker
              stack, or values from your deployment.
            </Text>
            <Text size="sm" fw={600}>
              README — local Docker
            </Text>
            <Code block>
              {README_LOCAL_EMAIL}
              {"\n"}
              {README_LOCAL_PASSWORD}
            </Code>
            <Text size="xs" c="dimmed">
              For a public demo host, rebuild the frontend with{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_EMAIL
              </Text>{" "}
              and{" "}
              <Text span ff="monospace" size="xs">
                NEXT_PUBLIC_DEMO_LOGIN_PASSWORD
              </Text>{" "}
              matching <Text span ff="monospace">BOOTSTRAP_ADMIN_*</Text>.
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
            {branding.logo_url ? (
              <img src={branding.logo_url} alt={branding.name} style={{ height: 36 }} />
            ) : (
              <Title order={3} c="dark.9">
                {branding.name}
              </Title>
            )}
          </Group>
          <Text size="sm" c="dimmed">
            Sign in with your account
          </Text>
        </Box>
        {error ? (
          <Alert icon={<IconAlertCircle size={18} />} color="dark" variant="light" title="Sign-in error">
            {error}
          </Alert>
        ) : null}
        <form onSubmit={handleSubmit}>
          <Stack gap="sm">
            <TextInput
              id="sign-in-email"
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <PasswordInput label="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <Button type="submit" loading={loading} fullWidth mt="xs" size="md" color="dark">
              Sign in
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
              Back to welcome
            </Button>
          ) : null}
          <Title order={1} fz={{ base: 28, sm: 34 }}>
            Sign in
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
            <Anchor
              component="button"
              type="button"
              c="dark"
              fw={600}
              style={{ background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
              onClick={() => {
                localStorage.removeItem(WELCOME_LS_KEY);
                setFullWelcome(true);
                setWelcomeChecked(true);
                setAuthStep("welcome");
              }}
            >
              Show full welcome page
            </Anchor>
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
      <Container fluid px={fluidPx} pt="md" pb="xl" w="100%">
        <Stack gap="xl" w="100%">
          <Stack gap={4} align="center" w="100%">
            <Group gap="sm" justify="center">
              {branding.logo_url ? (
                <img src={branding.logo_url} alt={branding.name} style={{ height: 44 }} />
              ) : (
                <Title order={2}>{branding.name}</Title>
              )}
            </Group>
            <Text size="sm" c="dimmed" ta="center" w="100%" maw="100%">
              AI-native, composable ERP/CRM engine — build vertical apps on a registry-driven stack, not a rigid SKU.
            </Text>
          </Stack>

          <Stack gap="md" align="center" w="100%">
            <Title order={1} ta="center" fz={{ base: 26, sm: 34 }} fw={700} w="100%">
              Welcome to your Orbiteus installation
            </Title>
            <Text c="dimmed" ta="center" lh={1.65} w="100%" size="md">
              This page is the public entry to your demo instance: the same Next.js + FastAPI codebase as in the
              repository, with live PostgreSQL, auto-generated CRUD, registry-driven modules, Command Palette (⌘K), and
              OpenAPI per model — a modular onboarding layout tailored for Orbiteus.
            </Text>
          </Stack>

          <Alert color="dark" variant="outline" title="Demo & security">
            <List spacing="xs" size="sm" mt="xs" withPadding>
              <List.Item>
                The next step shows the sign-in form and, when configured at build time, the public demo email/password
                pair for this host. Otherwise you see README defaults for local development only.
              </List.Item>
              <List.Item>
                After first login, rotate passwords and tighten{" "}
                <Text span fw={600}>
                  SECRET_KEY
                </Text>{" "}
                / bootstrap settings before any production traffic.
              </List.Item>
              <List.Item>
                Reference stack and defaults are documented in the{" "}
                <Anchor href="https://github.com/orbiteus/orbiteus" target="_blank" rel="noreferrer" fw={600}>
                  GitHub README
                </Anchor>
                .
              </List.Item>
            </List>
          </Alert>

          <Box w="100%">
            <Title order={3} mb="md" ta="center">
              Choose how you will use this demo
            </Title>
            <Text c="dimmed" ta="center" mb="lg" size="sm" w="100%">
              One JWT session for everyone — pick a path below to open the sign-in step. The same bootstrap account
              applies; cards describe what you can do after authentication.
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
                        Available in this build
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
              API resources
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md" w="100%">
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  OpenAPI / Swagger
                </Text>
                <Text size="xs" c="dimmed">
                  Interactive HTTP reference for every registered route.
                </Text>
                <Anchor href="/api/docs" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  Open API docs →
                </Anchor>
              </Paper>
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  OpenAPI JSON
                </Text>
                <Text size="xs" c="dimmed">
                  Machine-readable OpenAPI 3 schema for codegen and tests.
                </Text>
                <Anchor href="/api/openapi.json" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  Download JSON →
                </Anchor>
              </Paper>
              <Paper withBorder p="md" component={Stack} gap="xs">
                <Text fw={700} size="sm">
                  Repository
                </Text>
                <Text size="xs" c="dimmed">
                  Source, issues, and contribution workflow.
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
                  Product site
                </Text>
                <Text size="xs" c="dimmed">
                  Positioning, licensing, and contact.
                </Text>
                <Anchor href="https://orbiteus.com" target="_blank" rel="noreferrer" size="sm" fw={600}>
                  <Group gap={6} wrap="nowrap">
                    <IconBook size={16} /> orbiteus.com
                  </Group>
                </Anchor>
              </Paper>
            </SimpleGrid>
            <Text size="sm" mt="md" c="dimmed">
              Current API base URL:{" "}
              <Text span ff="monospace" size="sm" c="dark.8">
                {apiBase}
              </Text>
            </Text>
          </Box>

          <Checkbox
            checked={welcomeChecked}
            onChange={(e) => saveWelcomePreference(e.currentTarget.checked)}
            label="Display this welcome page next time"
            color="dark"
          />

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" w="100%">
            <Paper withBorder p="md">
              <Group gap="sm" mb="sm">
                <ThemeIcon variant="outline" color="dark" size="md" radius="md">
                  <IconDatabase size={18} />
                </ThemeIcon>
                <Title order={4}>Database status</Title>
              </Group>
              {metaLoading ? (
                <Loader size="sm" color="dark" />
              ) : healthErr ? (
                <Text size="sm" c="dimmed">
                  Could not reach <Text span ff="monospace">/api/base/health</Text>. Is the backend up?
                </Text>
              ) : (
                <Stack gap={4}>
                  <Text size="sm">
                    Status:{" "}
                    <Text span fw={700} tt="uppercase">
                      {health?.status ?? "unknown"}
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
                Active modules
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
                        Models: {m.models?.length ?? 0}
                      </Text>
                    </Paper>
                  ))}
                </SimpleGrid>
              )}
            </Paper>
          </SimpleGrid>

          <Stack gap="xs" align="center" pt="md" w="100%">
            <Group gap="md" justify="center" wrap="wrap">
              <Anchor href="/login" size="sm" c="dark" fw={600}>
                Welcome
              </Anchor>
              <Text size="sm" c="dimmed">
                ·
              </Text>
              <Anchor href="https://github.com/orbiteus/orbiteus/blob/main/README.md" size="sm" c="dark" fw={600}>
                README
              </Anchor>
              <Text size="sm" c="dimmed">
                ·
              </Text>
              <Anchor href="/api/docs" size="sm" c="dark" fw={600}>
                API docs
              </Anchor>
            </Group>
            <Text size="xs" c="dimmed" ta="center">
              Built with Next.js 14, FastAPI, SQLAlchemy 2 (async), and Mantine — modular by design.
            </Text>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}
