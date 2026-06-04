"use client";

import { Group, Text, Tooltip } from "@mantine/core";
import {
  IconDeviceDesktop,
  IconDeviceMobile,
  IconDeviceTablet,
  IconHelp,
} from "@tabler/icons-react";
import { formatListDate } from "@/lib/formatters";
import { useI18n, DAYJS_LOCALE, resolveDayjsLocale } from "@orbiteus/i18n";

type LoginDeviceKind = "desktop" | "mobile" | "tablet" | "unknown";

function normalizeDevice(value: unknown): LoginDeviceKind {
  const s = String(value ?? "").toLowerCase();
  if (s === "desktop" || s === "mobile" || s === "tablet") return s;
  return "unknown";
}

export function LastLoginCell({
  lastLogin,
  device,
}: {
  lastLogin: unknown;
  device?: unknown;
}) {
  const { t, locale } = useI18n();
  const dayjsLocale = resolveDayjsLocale(locale, DAYJS_LOCALE);

  if (lastLogin == null || lastLogin === "") {
    return (
      <Text size="sm" c="dimmed">
        {t("common.never")}
      </Text>
    );
  }

  const kind = normalizeDevice(device);
  const labelKey = `device.${kind}` as const;
  const icons = {
    desktop: IconDeviceDesktop,
    mobile: IconDeviceMobile,
    tablet: IconDeviceTablet,
    unknown: IconHelp,
  } as const;
  const Icon = icons[kind];

  return (
    <Group gap={6} wrap="nowrap">
      <Tooltip label={t(labelKey)} withArrow openDelay={200}>
        <Icon size={16} stroke={1.5} aria-label={t(labelKey)} />
      </Tooltip>
      <Text size="sm">{formatListDate(lastLogin, dayjsLocale)}</Text>
    </Group>
  );
}
