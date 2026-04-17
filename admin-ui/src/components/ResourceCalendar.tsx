"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Divider,
  Group,
  Loader,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import dayjs from "dayjs";
import { api } from "@/lib/api";
import { humanizeFieldName, useI18n } from "@/lib/i18n";

interface Props {
  resource: string;
  /** Field holding the event date (ISO string or date) */
  dateField: string;
  titleField?: string;
}

type CalendarView = "month" | "week" | "day";

interface CalendarEvent {
  id: string;
  title: string;
  dayKey: string;
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function ResourceCalendar({ resource, dateField, titleField = "name" }: Props) {
  const { t } = useI18n();
  const [view, setView] = useState<CalendarView>("month");
  const [anchorDate, setAnchorDate] = useState<Date>(new Date());
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/${resource}`, { params: { limit: 500 } })
      .then((res) => {
        setRows(res.data.items ?? res.data ?? []);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [resource]);

  const events = useMemo<CalendarEvent[]>(() => {
    const q = query.trim().toLowerCase();
    const out: CalendarEvent[] = [];
    for (const r of rows) {
      const raw = r[dateField];
      if (raw == null || raw === "") continue;
      const d = dayjs(String(raw).slice(0, 10));
      if (!d.isValid()) continue;
      const title = String(r[titleField] ?? r.id ?? "");
      if (q && !title.toLowerCase().includes(q)) continue;
      out.push({
        id: String(r.id ?? `${d.valueOf()}-${title}`),
        title,
        dayKey: d.format("YYYY-MM-DD"),
      });
    }
    return out;
  }, [rows, dateField, titleField, query]);

  const eventsByDay = useMemo(() => {
    const m = new Map<string, CalendarEvent[]>();
    for (const ev of events) {
      if (!m.has(ev.dayKey)) m.set(ev.dayKey, []);
      m.get(ev.dayKey)!.push(ev);
    }
    return m;
  }, [events]);

  const monthKey = dayjs(anchorDate).format("YYYY-MM");
  const gridDays = useMemo(() => {
    const out: dayjs.Dayjs[] = [];
    const start = dayjs(anchorDate).startOf("month").startOf("week");
    const end = dayjs(anchorDate).endOf("month").endOf("week");
    let cur = start;
    while (cur.isBefore(end) || cur.isSame(end, "day")) {
      out.push(cur);
      cur = cur.add(1, "day");
    }
    return out;
  }, [anchorDate]);

  const weekDays = useMemo(() => {
    const start = dayjs(anchorDate).startOf("week");
    return Array.from({ length: 7 }, (_, i) => start.add(i, "day"));
  }, [anchorDate]);

  const selectedKey = dayjs(selectedDate).format("YYYY-MM-DD");
  const selectedEvents = eventsByDay.get(selectedKey) ?? [];
  const dateFieldLabel = humanizeFieldName(dateField);

  const visibleAgenda = useMemo(
    () =>
      Array.from(eventsByDay.entries())
        .filter(([d]) => {
          if (view === "month") return d.startsWith(monthKey);
          if (view === "week") {
            const start = dayjs(anchorDate).startOf("week");
            const end = dayjs(anchorDate).endOf("week");
            const cur = dayjs(d);
            return (cur.isAfter(start) || cur.isSame(start, "day"))
              && (cur.isBefore(end) || cur.isSame(end, "day"));
          }
          return d === selectedKey;
        })
        .sort((a, b) => a[0].localeCompare(b[0])),
    [eventsByDay, monthKey, view, anchorDate, selectedKey],
  );

  if (loading) return <Loader color="gray" size="sm" />;

  function shiftPeriod(dir: -1 | 1) {
    const unit = view === "month" ? "month" : view === "week" ? "week" : "day";
    const next = dayjs(anchorDate).add(dir, unit).toDate();
    setAnchorDate(next);
    if (view === "day") setSelectedDate(next);
  }

  function renderMonthGrid() {
    return (
      <Box style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 1 }}>
        {WEEKDAYS.map((d) => (
          <Box key={d} p={8} style={{ background: "var(--mantine-color-gray-0)", textAlign: "center" }}>
            <Text size="xs" fw={700} c="dimmed">{d}</Text>
          </Box>
        ))}
        {gridDays.map((d) => {
          const key = d.format("YYYY-MM-DD");
          const list = eventsByDay.get(key) ?? [];
          const isCurrentMonth = d.month() === dayjs(anchorDate).month();
          const isSelected = key === selectedKey;
          return (
            <Box
              key={key}
              p={8}
              onClick={() => setSelectedDate(d.toDate())}
              style={{
                minHeight: 140,
                border: "1px solid var(--mantine-color-default-border)",
                cursor: "pointer",
                background: isSelected ? "var(--mantine-color-blue-0)" : "var(--mantine-color-body)",
                opacity: isCurrentMonth ? 1 : 0.45,
              }}
            >
              <Group justify="space-between" mb={6}>
                <Text size="xs" fw={700}>{d.date()}</Text>
                {list.length > 0 && <Badge size="xs" variant="light">{list.length}</Badge>}
              </Group>
              <Stack gap={4}>
                {list.slice(0, 3).map((ev) => (
                  <Text
                    key={ev.id}
                    size="xs"
                    truncate
                    style={{
                      padding: "2px 6px",
                      borderRadius: 6,
                      background: "var(--mantine-color-blue-1)",
                    }}
                  >
                    {ev.title}
                  </Text>
                ))}
                {list.length > 3 && (
                  <Text size="xs" c="dimmed">+{list.length - 3} more</Text>
                )}
              </Stack>
            </Box>
          );
        })}
      </Box>
    );
  }

  function renderWeekGrid() {
    return (
      <Box style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 8 }}>
        {weekDays.map((d) => {
          const key = d.format("YYYY-MM-DD");
          const list = eventsByDay.get(key) ?? [];
          return (
            <Paper
              key={key}
              p="sm"
              withBorder
              radius="sm"
              style={{ minHeight: 260, cursor: "pointer" }}
              onClick={() => setSelectedDate(d.toDate())}
            >
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={700}>{d.format("ddd D")}</Text>
                {list.length > 0 && <Badge size="xs" variant="light">{list.length}</Badge>}
              </Group>
              <Stack gap={4}>
                {list.length > 0 ? list.map((ev) => (
                  <Text
                    key={ev.id}
                    size="xs"
                    truncate
                    style={{
                      padding: "3px 6px",
                      borderRadius: 6,
                      background: "var(--mantine-color-blue-0)",
                    }}
                  >
                    {ev.title}
                  </Text>
                )) : <Text size="xs" c="dimmed">{t("no_events")}</Text>}
              </Stack>
            </Paper>
          );
        })}
      </Box>
    );
  }

  function renderDayView() {
    return (
      <Paper withBorder p="md" radius="sm">
        <Title order={5} mb="sm">{dayjs(selectedDate).format("dddd, D MMMM YYYY")}</Title>
        <Divider mb="sm" />
        <Stack gap="xs">
          {selectedEvents.length > 0 ? selectedEvents.map((ev) => (
            <Paper key={ev.id} p="sm" withBorder radius="sm">
              <Text size="sm">{ev.title}</Text>
            </Paper>
          )) : <Text size="sm" c="dimmed">{t("no_events_on_selected_day")}</Text>}
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack gap="md">
      <Title order={4}>{t("calendar_by", { field: dateFieldLabel })}</Title>
      <Paper withBorder p="md" radius="sm">
        <Stack gap="sm">
          <Group justify="space-between" wrap="wrap">
            <Group gap="xs">
              <ActionIcon variant="light" onClick={() => shiftPeriod(-1)} aria-label="Previous period">
                <IconChevronLeft size={16} />
              </ActionIcon>
              <ActionIcon variant="light" onClick={() => shiftPeriod(1)} aria-label="Next period">
                <IconChevronRight size={16} />
              </ActionIcon>
              <Button
                variant="subtle"
                size="xs"
                onClick={() => {
                  const now = new Date();
                  setAnchorDate(now);
                  setSelectedDate(now);
                }}
              >
                {t("today")}
              </Button>
            </Group>
            <Group gap="sm">
              <SegmentedControl
                size="xs"
                value={view}
                onChange={(v) => setView(v as CalendarView)}
                data={[
                  { label: t("month"), value: "month" },
                  { label: t("week"), value: "week" },
                  { label: t("day"), value: "day" },
                ]}
              />
              <TextInput
                size="xs"
                w={220}
                placeholder={t("filter_events")}
                value={query}
                onChange={(e) => setQuery(e.currentTarget.value)}
              />
            </Group>
          </Group>
          <Group justify="space-between">
            <Title order={4}>
              {view === "month" && dayjs(anchorDate).format("MMMM YYYY")}
              {view === "week" && `${weekDays[0].format("D MMM")} - ${weekDays[6].format("D MMM YYYY")}`}
              {view === "day" && dayjs(selectedDate).format("D MMMM YYYY")}
            </Title>
            <Text size="xs" c="dimmed">{t("events", { count: events.length })}</Text>
          </Group>
          {view === "month" && renderMonthGrid()}
          {view === "week" && renderWeekGrid()}
          {view === "day" && renderDayView()}
        </Stack>
      </Paper>

      <Paper withBorder p="md" radius="sm">
        <Title order={5} mb="xs">{t("events_list")}</Title>
        <Text size="sm" c="dimmed" mb="sm">
          {view === "day"
            ? t("selected_day", { date: selectedKey })
            : t("filtered_period", { period: t(view) })}
        </Text>
        <Stack gap="xs">
          {selectedEvents.length > 0
            ? selectedEvents.map((ev) => <Text key={ev.id} size="sm">{ev.title}</Text>)
            : <Text size="sm" c="dimmed">{t("no_events_on_selected_day")}</Text>}
        </Stack>
      </Paper>

      <Paper withBorder p="md" radius="sm">
        <Title order={5} mb="xs">{t("agenda")}</Title>
        <Stack gap="xs">
          {visibleAgenda.length > 0 ? visibleAgenda.map(([d, dayEvents]) => (
            <Box key={d}>
              <Text size="xs" c="dimmed" mb={2}>{d}</Text>
              {dayEvents.map((ev) => (
                <Text key={ev.id} size="sm">{ev.title}</Text>
              ))}
            </Box>
          )) : (
            <Text size="sm" c="dimmed">{t("no_records_for_period")}</Text>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
