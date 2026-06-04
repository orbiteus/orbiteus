"use client";

import { ActionIcon, Group, Loader, Stack, Text, TextInput } from "@mantine/core";
import { IconAlertTriangle, IconArrowUp } from "@tabler/icons-react";
import { useState } from "react";
import { useT } from "@orbiteus/i18n";

import type { AIScope } from "./types";
import { useAIContext } from "./useAIContext";

interface Props {
  scope: AIScope;
  placeholder?: string;
  agentId?: string;
  stream?: boolean;
}

/**
 * Embeddable prompt input. Drop into any page to enable AI on that surface.
 * Renders a graceful empty state when no AI credential is configured.
 */
export function PromptInput({
  scope,
  placeholder,
  agentId,
  stream = false,
}: Props) {
  const t = useT();
  const { messages, loading, error, hasCredential, send } = useAIContext({
    scope,
    agentId,
    stream,
  });
  const resolvedPlaceholder = placeholder ?? t("ai.promptInput.placeholder");
  const [draft, setDraft] = useState("");

  if (hasCredential === false) {
    return (
      <Stack gap={4}>
        <Group gap={6}>
          <IconAlertTriangle size={16} />
          <Text size="sm" c="dimmed">
            {t("ai.promptInput.noCredential")} <Text span fw={600}>/api/ai/credentials</Text>.
          </Text>
        </Group>
      </Stack>
    );
  }

  return (
    <Stack gap="xs">
      {messages.map((m, i) => (
        <Text key={i} size="sm" c={m.role === "assistant" ? "dark.6" : "dark.9"}>
          <Text span fw={600}>{m.role}: </Text>
          {m.content}
        </Text>
      ))}
      {error ? (
        <Text size="sm" c="red">
          {error}
        </Text>
      ) : null}
      <Group gap="xs" wrap="nowrap" align="end">
        <TextInput
          flex={1}
          placeholder={resolvedPlaceholder}
          value={draft}
          onChange={(e) => setDraft(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && draft.trim() && !loading) {
              send(draft.trim());
              setDraft("");
            }
          }}
        />
        {loading ? (
          <Loader size="sm" />
        ) : (
          <ActionIcon
            variant="filled"
            color="dark"
            disabled={!draft.trim()}
            onClick={() => {
              if (draft.trim()) {
                send(draft.trim());
                setDraft("");
              }
            }}
            aria-label={t("ai.promptInput.send")}
          >
            <IconArrowUp size={16} />
          </ActionIcon>
        )}
      </Group>
    </Stack>
  );
}
