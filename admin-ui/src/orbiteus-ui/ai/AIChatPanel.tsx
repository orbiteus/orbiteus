"use client";

import { Drawer, Stack, Title } from "@mantine/core";
import { useT } from "@orbiteus/i18n";

import { PromptInput } from "./PromptInput";
import type { AIScope } from "./types";

interface Props {
  scope: AIScope;
  opened: boolean;
  onClose: () => void;
  title?: string;
  stream?: boolean;
  agentId?: string;
}

/** Drawer-style chat panel built on top of `<PromptInput>`. */
export function AIChatPanel({
  scope,
  opened,
  onClose,
  title,
  stream = false,
  agentId,
}: Props) {
  const t = useT();
  const resolvedTitle = title ?? t("common.assistant");
  return (
    <Drawer position="right" size="md" opened={opened} onClose={onClose} withCloseButton>
      <Stack gap="md" h="100%">
        <Title order={4}>{resolvedTitle}</Title>
        <PromptInput scope={scope} stream={stream} agentId={agentId} />
      </Stack>
    </Drawer>
  );
}
