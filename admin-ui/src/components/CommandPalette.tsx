"use client";
/**
 * CommandPalette — Cmd+K global modal with AI-powered action search.
 *
 * Architecture:
 *  - Cmd+K (or Ctrl+K) opens the modal globally
 *  - User types → debounced GET /api/ai/actions?q=
 *  - Results grouped by category, keyboard navigable (↑↓ Enter Esc)
 *  - Selecting an action → router.push(action.target_url)
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Modal, TextInput, Stack, Text, Group, Badge, UnstyledButton,
  Loader, Box,
} from "@mantine/core";
import { IconSearch, IconPlus, IconList,
         IconChartBar, IconBolt, IconHistory } from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api } from "@/lib/api";
import { isAllowedAppPath } from "@/lib/knownModels";
import { useUiConfig } from "@/lib/queries/uiConfig";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ActionResult {
  id: string;
  label: string;
  description: string;
  category: string;
  target: string;
  target_url: string;
  icon: string;
  module: string;
}

interface ScoredAction {
  action: ActionResult;
  score: number;
}

const RECENT_STORAGE_KEY = "orbiteus.commandPalette.recent";
const RECENT_MAX = 5;

function loadRecentActions(uiConfig: ReturnType<typeof useUiConfig>["data"]): ActionResult[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ActionResult[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((a) => isAllowedAppPath(a.target_url, uiConfig));
  } catch {
    return [];
  }
}

function rememberAction(action: ActionResult) {
  if (typeof window === "undefined") return;
  let prev: ActionResult[] = [];
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ActionResult[];
      if (Array.isArray(parsed)) {
        prev = parsed.filter((a) => a.id !== action.id);
      }
    }
  } catch {
    prev = [];
  }
  prev.unshift(action);
  try {
    localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(prev.slice(0, RECENT_MAX)));
  } catch {
    /* ignore quota */
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const KNOWN_CATEGORIES = new Set(["navigate", "create", "report", "execute", "search"]);

const CATEGORY_ORDER = ["create", "navigate", "search", "report", "execute"];

function CategoryIcon({ category }: { category: string }) {
  const props = { size: 14, stroke: 1.5 };
  switch (category) {
    case "create":   return <IconPlus {...props} />;
    case "navigate": return <IconList {...props} />;
    case "report":   return <IconChartBar {...props} />;
    case "execute":  return <IconBolt {...props} />;
    case "search":   return <IconSearch {...props} />;
    default:         return <IconList {...props} />;
  }
}

function groupByCategory(results: ScoredAction[]): Map<string, ScoredAction[]> {
  const map = new Map<string, ScoredAction[]>();
  for (const r of results) {
    const cat = r.action.category;
    if (!map.has(cat)) map.set(cat, []);
    map.get(cat)!.push(r);
  }
  // Sort groups by predefined order
  const sorted = new Map<string, ScoredAction[]>();
  for (const cat of CATEGORY_ORDER) {
    if (map.has(cat)) sorted.set(cat, map.get(cat)!);
  }
  // Append any unknown categories
  for (const [k, v] of map) {
    if (!sorted.has(k)) sorted.set(k, v);
  }
  return sorted;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CommandPalette() {
  const t = useT();
  const router = useRouter();
  const uiConfig = useUiConfig();
  const [opened, setOpened] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ScoredAction[]>([]);
  const [recentPlain, setRecentPlain] = useState<ActionResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wasSearchRef = useRef(false);

  // ---- Open/close via Cmd+K ----
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpened((o) => !o);
      }
      if (e.key === "Escape") {
        setOpened(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // ---- Focus input when opened ----
  useEffect(() => {
    if (opened) {
      wasSearchRef.current = false;
      setQuery("");
      setResults([]);
      setRecentPlain(loadRecentActions(uiConfig.data));
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [opened, uiConfig.data]);

  // ---- Debounced search ----
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const q = query.trim();
    if (!q) {
      setResults([]);
      setLoading(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get("/ai/actions", {
          params: { q: query, limit: 12 },
          skipGlobalErrorToast: true,
        });
        // Backend returns `{ items: [...] }`; older paths shipped
        // `{ results: [...] }`. Read both so the palette works against
        // either contract.
        setResults((data?.items ?? data?.results ?? []) as ScoredAction[]);
        setActiveIdx(0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 150);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  useEffect(() => {
    const searching = query.trim().length > 0;
    if (searching !== wasSearchRef.current) setActiveIdx(0);
    wasSearchRef.current = searching;
  }, [query]);

  // ---- Keyboard navigation inside list ----
  function onInputKeyDown(e: React.KeyboardEvent) {
    const searching = query.trim().length > 0;
    const navLen = searching ? results.length : recentPlain.length;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, Math.max(navLen - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (searching) {
        if (results[activeIdx]) execute(results[activeIdx].action);
      } else if (recentPlain[activeIdx]) {
        execute(recentPlain[activeIdx]);
      }
    }
  }

  const execute = useCallback((action: ActionResult) => {
    if (!isAllowedAppPath(action.target_url, uiConfig.data)) {
      setOpened(false);
      return;
    }
    rememberAction(action);
    setOpened(false);
    if (action.target === "navigate" || action.target === "modal") {
      router.push(action.target_url);
    } else if (action.target === "execute" && action.target_url) {
      router.push(action.target_url);
    }
  }, [router, uiConfig.data]);

  const grouped = groupByCategory(results);

  let absIdx = 0;
  const indexMap = new Map<string, number>();
  for (const items of grouped.values()) {
    for (const item of items) {
      indexMap.set(item.action.id, absIdx++);
    }
  }

  const navListLen = query.trim().length > 0 ? results.length : recentPlain.length;

  return (
    <Modal
      opened={opened}
      onClose={() => setOpened(false)}
      withCloseButton={false}
      size={520}
      padding={0}
      radius="md"
      styles={{
        content: {
          background: "var(--mantine-color-body)",
          border: "1px solid var(--mantine-color-default-border)",
          overflow: "hidden",
        },
        overlay: { backdropFilter: "blur(2px)" },
      }}
    >
      {/* Search input */}
      <Box
        p="sm"
        style={{ borderBottom: "1px solid var(--mantine-color-default-border)" }}
      >
        <TextInput
          ref={inputRef}
          placeholder={t("palette.ask")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onInputKeyDown}
          leftSection={
            loading
              ? <Loader size={14} color="gray" />
              : <IconSearch size={16} stroke={1.5} color="var(--mantine-color-gray-5)" />
          }
          variant="unstyled"
          size="md"
          styles={{
            input: {
              color: "var(--mantine-color-text)",
              fontSize: 15,
              background: "transparent",
              "&::placeholder": { color: "var(--mantine-color-gray-6)" },
            },
          }}
        />
      </Box>

      {/* Results */}
      <Box style={{ maxHeight: 400, overflowY: "auto" }} p="xs">
        {query.trim().length > 0 && results.length === 0 && !loading && (
          <Text size="sm" c="dimmed" ta="center" py="md">
            {t("palette.noResultsFor", { query })}
          </Text>
        )}

        {query.trim().length === 0 && recentPlain.length === 0 && !loading && (
          <Text size="xs" c="dimmed" ta="center" py="sm">
            {t("palette.startTyping")}
          </Text>
        )}

        {query.trim().length === 0 && recentPlain.length > 0 && (
          <Box mb={8}>
            <Text
              size="xs" fw={700} tt="uppercase" c="dimmed" px={8} pb={4}
              style={{ letterSpacing: "0.06em" }}
            >
              {t("palette.recent")}
            </Text>
            {recentPlain.map((action, idx) => {
              const isActive = idx === activeIdx;
              return (
                <UnstyledButton
                  key={`recent-${action.id}-${idx}`}
                  onClick={() => execute(action)}
                  onMouseEnter={() => setActiveIdx(idx)}
                  w="100%"
                  px={8} py={6}
                  style={{
                    borderRadius: "var(--mantine-radius-sm)",
                    background: isActive
                      ? "var(--mantine-color-dark-0)"
                      : "transparent",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                  }}
                >
                  <Box c={isActive ? "dark" : "dimmed"} style={{ lineHeight: 1 }}>
                    <IconHistory size={14} stroke={1.5} />
                  </Box>
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Text size="sm" c={isActive ? "dark.9" : "dimmed"} truncate>
                      {action.label}
                    </Text>
                    {action.description && (
                      <Text size="xs" c="dimmed" truncate>
                        {action.description}
                      </Text>
                    )}
                  </Box>
                  {action.module && (
                    <Badge
                      size="xs" variant="light" color="gray"
                      style={{ flexShrink: 0, textTransform: "uppercase" }}
                    >
                      {action.module}
                    </Badge>
                  )}
                </UnstyledButton>
              );
            })}
          </Box>
        )}

        {query.trim().length > 0 && Array.from(grouped.entries()).map(([category, items]) => (
          <Box key={category} mb={8}>
            <Text
              size="xs" fw={700} tt="uppercase" c="dimmed" px={8} pb={4}
              style={{ letterSpacing: "0.06em" }}
            >
              {KNOWN_CATEGORIES.has(category) ? t(`palette.category.${category}`) : category}
            </Text>
            {items.map((item) => {
              const idx = indexMap.get(item.action.id) ?? 0;
              const isActive = idx === activeIdx;
              return (
                <UnstyledButton
                  key={item.action.id}
                  onClick={() => execute(item.action)}
                  onMouseEnter={() => setActiveIdx(idx)}
                  w="100%"
                  px={8} py={6}
                  style={{
                    borderRadius: "var(--mantine-radius-sm)",
                    background: isActive
                      ? "var(--mantine-color-dark-0)"
                      : "transparent",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                  }}
                >
                  <Box c={isActive ? "dark" : "dimmed"} style={{ lineHeight: 1 }}>
                    <CategoryIcon category={category} />
                  </Box>
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Text size="sm" c={isActive ? "dark.9" : "dimmed"} truncate>
                      {item.action.label}
                    </Text>
                    {item.action.description && (
                      <Text size="xs" c="dimmed" truncate>
                        {item.action.description}
                      </Text>
                    )}
                  </Box>
                  {item.action.module && (
                    <Badge
                      size="xs" variant="light" color="gray"
                      style={{ flexShrink: 0, textTransform: "uppercase" }}
                    >
                      {item.action.module}
                    </Badge>
                  )}
                </UnstyledButton>
              );
            })}
          </Box>
        ))}
      </Box>

      {/* Footer hint */}
      {navListLen > 0 && (
        <Box
          px="sm" py={6}
          style={{
            borderTop: "1px solid var(--mantine-color-default-border)",
            display: "flex",
            gap: 12,
          }}
        >
          {[["↑↓", t("palette.hint.navigate")], ["↵", t("palette.hint.open")], ["Esc", t("palette.hint.close")]].map(([key, hint]) => (
            <Group key={key} gap={4}>
              <Badge size="xs" variant="default" style={{ fontFamily: "monospace" }}>{key}</Badge>
              <Text size="xs" c="dimmed">{hint}</Text>
            </Group>
          ))}
        </Box>
      )}
    </Modal>
  );
}
