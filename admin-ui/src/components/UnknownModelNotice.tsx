"use client";

import Link from "next/link";
import { Button, Paper, Stack, Text, Title } from "@mantine/core";
import { useT } from "@orbiteus/i18n";

export default function UnknownModelNotice({
  module,
  model,
}: {
  module: string;
  model: string;
}) {
  const t = useT();
  const dotted = `${module}.${model}`;

  return (
    <Paper withBorder p="xl" m="md">
      <Stack gap="md" maw={480}>
        <Title order={3}>{t("unknownModel.title")}</Title>
        <Text c="dimmed">{t("unknownModel.body", { model: dotted })}</Text>
        <Button component={Link} href="/" variant="light">
          {t("unknownModel.backDashboard")}
        </Button>
      </Stack>
    </Paper>
  );
}
