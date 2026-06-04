"use client";

import { useMemo } from "react";
import {
  Alert,
  Badge,
  Code,
  Group,
  List,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { IconInfoCircle, IconLanguage } from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { useUiLocales, useUiMessages } from "@/lib/queries/i18n";
import type { UiLocaleMeta } from "@/lib/api";

const MANIFEST_EXAMPLE = `"i18n": ["pl"],
"i18n_locales": [
  {"code": "pl", "label": "Polski", "dayjs": "pl"},
],`;

function isCoreLocale(row: UiLocaleMeta): boolean {
  return row.source === "core" || row.code === "en";
}

export default function LanguagesPage() {
  const t = useT();
  const localesQuery = useUiLocales();
  const enMessagesQuery = useUiMessages("en");

  const locales = localesQuery.data ?? [];
  const enKeyCount = useMemo(
    () => (enMessagesQuery.data ? Object.keys(enMessagesQuery.data).length : null),
    [enMessagesQuery.data],
  );

  const moduleLocales = locales.filter((row) => !isCoreLocale(row));

  if (localesQuery.isLoading) {
    return (
      <Stack align="center" py="xl">
        <Loader color="gray" size="sm" />
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Group gap="sm">
          <ThemeIcon variant="light" color="gray" size="lg">
            <IconLanguage size={20} />
          </ThemeIcon>
          <Title order={2}>{t("languages.page.title")}</Title>
        </Group>
        <Text size="sm" c="dimmed" maw={720}>
          {t("languages.page.subtitle")}
        </Text>
      </Stack>

      <Paper withBorder p="md" radius="md">
        <Stack gap="md">
          <Group justify="space-between" wrap="wrap">
            <Title order={4}>{t("languages.core.title")}</Title>
            <Badge variant="light" color="blue">
              {t("languages.badge.core")}
            </Badge>
          </Group>
          <Text size="sm">{t("languages.core.description")}</Text>
          <Table withTableBorder withColumnBorders striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("languages.table.code")}</Table.Th>
                <Table.Th>{t("languages.table.label")}</Table.Th>
                <Table.Th>{t("languages.core.path")}</Table.Th>
                <Table.Th>{t("languages.core.keyCount")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td>
                  <Code>en</Code>
                  <Badge size="xs" variant="outline" ml="xs">
                    {t("languages.core.canonical")}
                  </Badge>
                </Table.Td>
                <Table.Td>English</Table.Td>
                <Table.Td>
                  <Code>modules/base/i18n/en.json</Code>
                </Table.Td>
                <Table.Td>
                  {enKeyCount ?? (enMessagesQuery.isLoading ? "…" : "—")}
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </Stack>
      </Paper>

      <Paper withBorder p="md" radius="md">
        <Stack gap="sm">
          <Title order={4}>{t("languages.registered.title")}</Title>
          {locales.length === 0 ? (
            <Text size="sm" c="dimmed">
              {t("languages.registered.empty")}
            </Text>
          ) : (
            <Table withTableBorder withColumnBorders striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("languages.table.code")}</Table.Th>
                  <Table.Th>{t("languages.table.label")}</Table.Th>
                  <Table.Th>{t("languages.table.dayjs")}</Table.Th>
                  <Table.Th>{t("languages.table.source")}</Table.Th>
                  <Table.Th>{t("languages.table.module")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {locales.map((row) => (
                  <Table.Tr key={row.code}>
                    <Table.Td>
                      <Code>{row.code}</Code>
                    </Table.Td>
                    <Table.Td>{row.label}</Table.Td>
                    <Table.Td>
                      <Code>{row.dayjs}</Code>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={isCoreLocale(row) ? "blue" : "teal"}>
                        {isCoreLocale(row)
                          ? t("languages.badge.core")
                          : t("languages.badge.extension")}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Code>
                        {isCoreLocale(row)
                          ? "base"
                          : row.module
                            ? `modules/${row.module}/i18n/${row.code}.json`
                            : "—"}
                      </Code>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
          {moduleLocales.length > 0 && (
            <Text size="xs" c="dimmed">
              {moduleLocales.length} {t("languages.badge.extension").toLowerCase()}
              {moduleLocales.map((r) => r.module).filter(Boolean).length > 0 &&
                ` (${[...new Set(moduleLocales.map((r) => r.module).filter(Boolean))].join(", ")})`}
            </Text>
          )}
        </Stack>
      </Paper>

      <Alert
        variant="light"
        color="gray"
        icon={<IconInfoCircle size={18} />}
        title={t("languages.modulePack.title")}
      >
        <Stack gap="sm">
          <Text size="sm">{t("languages.modulePack.intro")}</Text>
          <List size="sm" spacing="xs">
            <List.Item>{t("languages.modulePack.step1")}</List.Item>
            <List.Item>{t("languages.modulePack.step2")}</List.Item>
            <List.Item>{t("languages.modulePack.step3")}</List.Item>
          </List>
          <Code block>{MANIFEST_EXAMPLE}</Code>
          <Text size="sm">{t("languages.modulePack.overrides")}</Text>
          <Text size="xs" c="dimmed">
            {t("languages.modulePack.linkDocs")} Reference pack:{" "}
            <Code>modules/locales</Code> (pl, de, fr).
          </Text>
        </Stack>
      </Alert>
    </Stack>
  );
}
