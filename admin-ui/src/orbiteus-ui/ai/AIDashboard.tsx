"use client";

import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Paper,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconChartBar } from "@tabler/icons-react";
import axios from "axios";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useT } from "@orbiteus/i18n";

import type { AIScope } from "./types";

interface Props {
  scope: AIScope;
  initialPrompt?: string;
}

/**
 * Aggregate spec the model returned. Surfaced under the chart so a
 * curious user can audit / copy the underlying query (and an SRE can
 * tell whether a missing-data result was AI's fault or RBAC's).
 */
interface DashboardSpec {
  model: string;
  group_by: string;
  op: "count" | "sum" | "avg" | "min" | "max";
  measure: string | null;
  title: string;
}

interface DashboardResponse {
  title: string;
  chart_type: "bar" | "line" | "pie";
  x_axis: string;       // canonical: "category"
  y_axis: string;       // canonical: "value"
  data: Array<{ category: string; value: number | null }>;
  spec: DashboardSpec;
  usage_tokens?: number;
}

/**
 * Prompt → aggregate spec → recharts.
 *
 * Flow on the backend (DoD §10):
 *
 *   1. The AI provider receives a tightly-shaped system prompt and
 *      replies with a JSON object: `{model, group_by, op, measure,
 *      title}`.
 *   2. Backend executes that aggregate through the same RBAC +
 *      tenant-filter path the repository layer uses (so the AI
 *      cannot read across tenants or fields it doesn't own).
 *   3. We get back `data: [{category, value}]` ready for recharts.
 *
 * The component renders three layers:
 *   - the prompt input,
 *   - the bar chart (or a clear empty state),
 *   - a "spec" pill row showing the model + group_by + op so the
 *     viewer always knows what's being aggregated.
 */
export function AIDashboard({ scope, initialPrompt = "" }: Props) {
  const t = useT();
  const [prompt, setPrompt] = useState(initialPrompt);
  const [response, setResponse] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post<DashboardResponse>("/api/ai/dashboard", { scope, prompt });
      setResponse(res.data);
    } catch (err: unknown) {
      const detail = (err as {
        response?: { data?: { detail?: unknown } };
      })?.response?.data?.detail;
      let msg = t("ai.dashboard.error.generate");
      if (typeof detail === "string") {
        msg = detail;
      } else if (detail && typeof detail === "object" && "message" in detail) {
        msg = String((detail as { message: string }).message);
      }
      setError(msg);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Paper p="md" withBorder>
      <Stack gap="sm">
        <Group gap="xs" align="end">
          <TextInput
            flex={1}
            placeholder={t("ai.dashboard.placeholder")}
            value={prompt}
            onChange={(e) => setPrompt(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void run();
              }
            }}
          />
          <Button
            onClick={() => void run()}
            loading={loading}
            color="dark"
            disabled={!prompt.trim()}
            leftSection={<IconChartBar size={16} />}
          >
            {t("ai.dashboard.generate")}
          </Button>
        </Group>

        {error ? (
          <Alert color="red" icon={<IconAlertCircle size={16} />}>
            {error}
          </Alert>
        ) : null}

        {loading ? (
          <Stack gap="xs">
            <Skeleton height={28} width="40%" radius="sm" />
            <Skeleton height={300} radius="sm" />
          </Stack>
        ) : null}

        {!loading && response ? (
          <Stack gap="xs">
            <Group justify="space-between" align="center">
              <Title order={5}>{response.title}</Title>
              {response.usage_tokens ? (
                <Badge variant="light" color="gray" size="sm">
                  {t("ai.dashboard.tokensUsed", { count: response.usage_tokens })}
                </Badge>
              ) : null}
            </Group>

            {response.data.length === 0 ? (
              <Alert color="gray" icon={<IconAlertCircle size={16} />}>
                {t("ai.dashboard.emptyData", { model: response.spec.model })}
              </Alert>
            ) : (
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={response.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey={response.x_axis} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey={response.y_axis} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <Group gap="xs" wrap="wrap">
              <Badge variant="dot" color="dark">
                {t("ai.dashboard.spec.model")} <Code>{response.spec.model}</Code>
              </Badge>
              <Badge variant="dot" color="dark">
                {t("ai.dashboard.spec.groupBy")} <Code>{response.spec.group_by}</Code>
              </Badge>
              <Badge variant="dot" color="dark">
                {t("ai.dashboard.spec.op")} <Code>{response.spec.op}</Code>
              </Badge>
              {response.spec.measure ? (
                <Badge variant="dot" color="dark">
                  {t("ai.dashboard.spec.measure")} <Code>{response.spec.measure}</Code>
                </Badge>
              ) : null}
            </Group>
            <Text size="xs" c="dimmed">
              {t("ai.dashboard.footerHint")}
            </Text>
          </Stack>
        ) : null}

        {!loading && !response && !error ? (
          <Text size="sm" c="dimmed">
            {t("ai.dashboard.examplesLabel")} <Code>count leads by stage</Code>,{" "}
            <Code>sum expected revenue per stage</Code>, <Code>average lead value by team</Code>.
          </Text>
        ) : null}
      </Stack>
    </Paper>
  );
}
