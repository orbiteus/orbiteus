"use client";
/**
 * Technical → Agent Console
 *
 * Run named agents with async execution + live SSE status via the
 * realtime hub (`base.agent-run` topics, docs/37-ai-agents.md).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconPlayerPlay, IconRobot, IconSparkles } from "@tabler/icons-react";
import axios from "axios";
import { useT } from "@orbiteus/i18n";

import { useAuth } from "@/lib/auth";
import { subscribeRealtimeTopic } from "@/lib/realtimeHub";
import { listTopic, recordTopic } from "@/lib/realtimeTopics";
import type { RealtimeMessage } from "@/lib/realtimeTypes";

interface AgentRow {
  id: string;
  name: string;
  slug: string;
  module_scope: string;
  is_active: boolean;
}

interface AgentRunRow {
  id: string;
  agent_id: string;
  status: string;
  input_prompt: string;
  output_text: string | null;
  tokens_used: number;
  error_message: string | null;
  tool_trace: Array<Record<string, unknown>>;
  create_date: string | null;
}

interface ActiveRun {
  id: string;
  status: string;
  output_text: string | null;
  error_message: string | null;
  tool_trace: Array<Record<string, unknown>>;
  tokens_used: number;
}

const AGENT_RUN_MODEL = "base.agent-run";

function statusColor(status: string): string {
  switch (status) {
    case "completed":
      return "green";
    case "running":
      return "blue";
    case "pending":
      return "yellow";
    case "failed":
      return "red";
    default:
      return "gray";
  }
}

export default function AgentConsolePage() {
  const t = useT();
  const { user, hydrated } = useAuth();
  const tenantId = user?.tenant_id ?? null;

  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);
  const [recentRuns, setRecentRuns] = useState<AgentRunRow[]>([]);

  const agentOptions = useMemo(
    () =>
      agents
        .filter((a) => a.is_active)
        .map((a) => ({
          value: a.id,
          label: `${a.name} (${a.slug})`,
        })),
    [agents],
  );

  const loadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const { data } = await axios.get<{ items: AgentRow[] }>("/api/base/agent", {
        params: { limit: 100, offset: 0 },
      });
      setAgents(data.items ?? []);
      if (!agentId && data.items?.length) {
        setAgentId(data.items[0].id);
      }
    } catch {
      setError(t("agentConsole.loadAgentsFailed"));
    } finally {
      setLoadingAgents(false);
    }
  }, [agentId]);

  const loadRecentRuns = useCallback(async () => {
    try {
      const { data } = await axios.get<{ items: AgentRunRow[] }>("/api/base/agent-run", {
        params: { limit: 10, offset: 0, order: "create_date desc" },
      });
      setRecentRuns(data.items ?? []);
    } catch {
      /* keep last list */
    }
  }, []);

  useEffect(() => {
    void loadAgents();
    void loadRecentRuns();
  }, [loadAgents, loadRecentRuns]);

  const applyRunMessage = useCallback((msg: RealtimeMessage) => {
    if (msg.event !== "agent_run.updated") return;
    const runId = msg.run_id ?? msg.record_id;
    if (!runId) return;

    setActiveRun((prev) => {
      if (prev && prev.id !== runId) return prev;
      return {
        id: runId,
        status: msg.status ?? prev?.status ?? "running",
        output_text: msg.output_text ?? prev?.output_text ?? null,
        error_message: msg.error_message ?? prev?.error_message ?? null,
        tool_trace: msg.tool_trace ?? prev?.tool_trace ?? [],
        tokens_used: msg.tokens_used ?? prev?.tokens_used ?? 0,
      };
    });

    if (msg.status === "completed" || msg.status === "failed") {
      setRunning(false);
      void loadRecentRuns();
    }
  }, [loadRecentRuns]);

  useEffect(() => {
    if (!tenantId || !activeRun?.id) return;

    const record = recordTopic(tenantId, AGENT_RUN_MODEL, activeRun.id);
    const list = listTopic(tenantId, AGENT_RUN_MODEL);

    const offRecord = subscribeRealtimeTopic(record, applyRunMessage);
    const offList = subscribeRealtimeTopic(list, () => {
      void loadRecentRuns();
    });

    return () => {
      offRecord();
      offList();
    };
  }, [tenantId, activeRun?.id, applyRunMessage, loadRecentRuns]);

  async function onRunAsync() {
    if (!agentId || !prompt.trim()) return;
    setError(null);
    setRunning(true);
    setActiveRun(null);

    try {
      const { data } = await axios.post<{ id: string; status: string }>("/api/ai/runs", {
        agent_id: agentId,
        prompt: prompt.trim(),
        async: true,
      });
      setActiveRun({
        id: data.id,
        status: data.status ?? "pending",
        output_text: null,
        error_message: null,
        tool_trace: [],
        tokens_used: 0,
      });
      void loadRecentRuns();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setError(typeof detail === "string" ? detail : t("agentConsole.startRunFailed"));
      setRunning(false);
    }
  }

  if (!hydrated) {
    return (
      <Group justify="center" py="xl">
        <Loader size="sm" />
      </Group>
    );
  }

  return (
    <Stack gap="md">
      <Paper p="md">
        <Group gap="sm">
          <IconSparkles size={22} stroke={1.5} />
          <Stack gap={0}>
            <Title order={3}>{t("nav.ai.agentConsole")}</Title>
            <Text size="sm" c="dimmed">
              {t("agentConsole.description")}
            </Text>
          </Stack>
        </Group>
      </Paper>

      {error ? (
        <Alert color="red" title={t("common.error")}>
          {error}
        </Alert>
      ) : null}

      <Paper p="md">
        <Stack gap="sm">
          <Select
            label={t("agentConsole.agent")}
            placeholder={t("agentConsole.chooseAgent")}
            data={agentOptions}
            value={agentId}
            onChange={setAgentId}
            leftSection={<IconRobot size={16} />}
            disabled={loadingAgents || agentOptions.length === 0}
            searchable
          />
          <Textarea
            label={t("agentConsole.prompt")}
            placeholder={t("agentConsole.promptPlaceholder")}
            minRows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              onClick={() => void onRunAsync()}
              loading={running}
              disabled={!agentId || !prompt.trim()}
            >
              {t("agentConsole.runAsync")}
            </Button>
          </Group>
        </Stack>
      </Paper>

      {activeRun ? (
        <Paper p="md">
          <Stack gap="xs">
            <Group gap="sm">
              <Text fw={600}>{t("agentConsole.activeRun")}</Text>
              <Badge color={statusColor(activeRun.status)}>{activeRun.status}</Badge>
              <Code>{activeRun.id}</Code>
            </Group>
            {activeRun.output_text ? (
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {activeRun.output_text}
              </Text>
            ) : running ? (
              <Group gap="xs">
                <Loader size="xs" />
                <Text size="sm" c="dimmed">
                  {t("agentConsole.waitingOutput")}
                </Text>
              </Group>
            ) : null}
            {activeRun.error_message ? (
              <Alert color="red">{activeRun.error_message}</Alert>
            ) : null}
            {activeRun.tool_trace.length > 0 ? (
              <ScrollArea.Autosize mah={200}>
                <Code block>{JSON.stringify(activeRun.tool_trace, null, 2)}</Code>
              </ScrollArea.Autosize>
            ) : null}
          </Stack>
        </Paper>
      ) : null}

      <Paper p="md">
        <Title order={5} mb="sm">
          {t("agentConsole.recentRuns")}
        </Title>
        {recentRuns.length === 0 ? (
          <Text size="sm" c="dimmed">
            {t("agentConsole.noRuns")}
          </Text>
        ) : (
          <Stack gap="xs">
            {recentRuns.map((run) => (
              <Group key={run.id} justify="space-between" wrap="nowrap">
                <Stack gap={2} style={{ minWidth: 0 }}>
                  <Text size="sm" lineClamp={1}>
                    {run.input_prompt || t("agentConsole.emptyPrompt")}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {run.create_date ? new Date(run.create_date).toLocaleString() : "—"}
                  </Text>
                </Stack>
                <Badge color={statusColor(run.status)}>{run.status}</Badge>
              </Group>
            ))}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
}
