"use client";
/**
 * Public welcome / marketing page (DoD §9.9).
 *
 * Lives at `/welcome` so the sign-in form on `/login` stays single-purpose.
 * The page is whitelisted in `proxy.ts` (`PUBLIC_PATHS`) — visitors can
 * land here without a session cookie.
 *
 * Vendor-neutral (per `AGENTS.md`): names only Orbiteus and the public
 * stack. No outbound links to third-party ERP demos, no competitor
 * trademarks. The headline + subheadline mirror the README.
 */
import { useEffect, useState } from "react";
import {
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Flex,
  Group,
  List,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconApi,
  IconArrowRight,
  IconBook,
  IconBrandGithub,
  IconCircleCheck,
  IconRobot,
  IconShieldLock,
  IconSparkles,
  IconUsers,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { useBranding } from "@/lib/branding";
import { PublicNavButton } from "@/components/PublicNavButton";

const fluidPx = { base: "md", sm: "xl", lg: "3rem", xl: "4rem" } as const;

type HealthJson = { status?: string; service?: string };

export default function WelcomePage() {
  const t = useT();
  const branding = useBranding();
  const [health, setHealth] = useState<HealthJson | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const roleCards: {
    title: string;
    blurb: string;
    features: string[];
    icon: typeof IconShieldLock;
  }[] = [
    {
      title: t("welcome.card.superadmin.title"),
      blurb: t("welcome.card.superadmin.blurb"),
      features: [
        t("welcome.card.superadmin.feature1"),
        t("welcome.card.superadmin.feature2"),
        t("welcome.card.superadmin.feature3"),
      ],
      icon: IconShieldLock,
    },
    {
      title: t("welcome.card.ops.title"),
      blurb: t("welcome.card.ops.blurb"),
      features: [
        t("welcome.card.ops.feature1"),
        t("welcome.card.ops.feature2"),
        t("welcome.card.ops.feature3"),
      ],
      icon: IconUsers,
    },
    {
      title: t("welcome.card.headless.title"),
      blurb: t("welcome.card.headless.blurb"),
      features: [
        t("welcome.card.headless.feature1"),
        t("welcome.card.headless.feature2"),
        t("welcome.card.headless.feature3"),
      ],
      icon: IconApi,
    },
  ];

  const platformPillars: {
    title: string;
    blurb: string;
    features: string[];
    icon: typeof IconRobot;
  }[] = [
    {
      title: t("welcome.pillar.agents.title"),
      blurb: t("welcome.pillar.agents.blurb"),
      features: [
        t("welcome.pillar.agents.feature1"),
        t("welcome.pillar.agents.feature2"),
        t("welcome.pillar.agents.feature3"),
      ],
      icon: IconRobot,
    },
    {
      title: t("welcome.pillar.aiNative.title"),
      blurb: t("welcome.pillar.aiNative.blurb"),
      features: [
        t("welcome.pillar.aiNative.feature1"),
        t("welcome.pillar.aiNative.feature2"),
        t("welcome.pillar.aiNative.feature3"),
      ],
      icon: IconSparkles,
    },
  ];

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/api/base/health");
        if (!r.ok) throw new Error("bad");
        const j = (await r.json()) as HealthJson;
        if (!cancelled) setHealth(j);
      } catch {
        if (!cancelled) setHealthErr(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box bg="gray.0" mih="100vh" w="100%" pb="xl">
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
                {branding.hydrated && branding.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={branding.logo_url}
                    alt={branding.name}
                    style={{ height: 44, width: "auto", display: "block" }}
                  />
                ) : (
                  <Title order={2} c="dark.9" style={{ lineHeight: 1.2 }}>
                    {branding.name}
                  </Title>
                )}
              </Group>
              <Text
                size="sm"
                c="dimmed"
                ta="left"
                maw={{ base: "100%", md: "42rem", lg: "50rem" }}
                lh={1.55}
              >
                {t("welcome.heroTagline")}
              </Text>
            </Flex>
          </Box>

          <Stack gap="md" align="flex-start" w="100%">
            <Title
              order={1}
              ta="left"
              fz={{ base: 26, sm: 34 }}
              fw={700}
              w="100%"
            >
              {t("welcome.title")}
            </Title>
            <Text
              c="dimmed"
              ta="left"
              lh={1.65}
              w="100%"
              maw={{ base: "100%", md: "48rem", lg: "56rem" }}
              size="md"
            >
              {t("welcome.intro")}
            </Text>
            <Group>
              <PublicNavButton
                href="/login"
                rightSection={<IconArrowRight size={18} />}
                color="dark"
                size="md"
              >
                {t("auth.signIn")}
              </PublicNavButton>
              <Button
                component="a"
                href="https://github.com/orbiteus/orbiteus"
                target="_blank"
                rel="noreferrer"
                variant="default"
                leftSection={<IconBrandGithub size={18} />}
              >
                {t("welcome.readmeGithub")}
              </Button>
            </Group>
          </Stack>

          <Box w="100%">
            <Title order={3} mb="md">
              {t("welcome.whatShips")}
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md" w="100%">
              {roleCards.map((card) => {
                const RoleIcon = card.icon;
                return (
                  <Card
                    key={card.title}
                    withBorder
                    padding="lg"
                    radius="md"
                    h="100%"
                  >
                    <Stack gap="sm" h="100%">
                      <ThemeIcon
                        variant="outline"
                        color="dark"
                        size="lg"
                        radius="md"
                      >
                        <RoleIcon size={22} stroke={1.5} />
                      </ThemeIcon>
                      <Title order={4}>{card.title}</Title>
                      <Text size="sm" c="dimmed">
                        {card.blurb}
                      </Text>
                      <List
                        spacing={4}
                        size="sm"
                        icon={
                          <ThemeIcon variant="white" color="dark" size={16}>
                            <IconCircleCheck size={14} />
                          </ThemeIcon>
                        }
                      >
                        {card.features.map((f) => (
                          <List.Item key={f}>{f}</List.Item>
                        ))}
                      </List>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          </Box>

          <Box w="100%">
            <Title order={3} mb="md">
              {t("welcome.platformPillars")}
            </Title>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md" w="100%">
              {platformPillars.map((pillar) => {
                const PillarIcon = pillar.icon;
                return (
                  <Card key={pillar.title} withBorder padding="lg" radius="md" h="100%">
                    <Stack gap="sm" h="100%">
                      <ThemeIcon variant="outline" color="dark" size="lg" radius="md">
                        <PillarIcon size={22} stroke={1.5} />
                      </ThemeIcon>
                      <Title order={4}>{pillar.title}</Title>
                      <Text size="sm" c="dimmed">
                        {pillar.blurb}
                      </Text>
                      <List
                        spacing={4}
                        size="sm"
                        icon={
                          <ThemeIcon variant="white" color="dark" size={16}>
                            <IconCircleCheck size={14} />
                          </ThemeIcon>
                        }
                      >
                        {pillar.features.map((f) => (
                          <List.Item key={f}>{f}</List.Item>
                        ))}
                      </List>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          </Box>

          <Box w="100%">
            <Group gap="sm" mb="xs">
              <ThemeIcon variant="light" color="dark" radius="xl" size="md">
                <IconSparkles size={16} />
              </ThemeIcon>
              <Title order={4}>{t("welcome.liveStatus")}</Title>
            </Group>
            <Group gap="xs">
              <Badge
                color={healthErr ? "red" : "green"}
                variant="light"
                size="lg"
              >
                {healthErr
                  ? t("welcome.backendUnreachable")
                  : health?.status
                    ? t("welcome.backendStatus", { status: health.status })
                    : t("welcome.pingingBackend")}
              </Badge>
              <Anchor href="/api/base/health" target="_blank" rel="noreferrer" size="sm">
                /api/base/health
              </Anchor>
              <Anchor href="/api/docs" target="_blank" rel="noreferrer" size="sm">
                <IconBook size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                {t("welcome.openapiDocs")}
              </Anchor>
            </Group>
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}
