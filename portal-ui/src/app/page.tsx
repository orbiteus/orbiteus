"use client";

import { Anchor, Container, Stack, Text, Title } from "@mantine/core";
import { useT } from "@orbiteus/i18n";

export default function PortalRoot() {
  return <PortalHome />;
}

function PortalHome() {
  const t = useT();
  return (
    <Container size="sm" py="xl">
      <Stack gap="md">
        <Title order={1}>{t("portal.title")}</Title>
        <Text c="dimmed">{t("portal.intro")}</Text>
        <Text size="sm" c="dimmed">{t("portal.noLink")}</Text>
        <Anchor href="https://orbiteus.com" target="_blank" rel="noreferrer">
          {t("portal.about")}
        </Anchor>
      </Stack>
    </Container>
  );
}
