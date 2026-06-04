"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader, Select, Text } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { api } from "@/lib/api";
import { relationToResource } from "@/lib/relationPath";

function optionLabel(row: Record<string, unknown>): string {
  const name = (row as { name?: string }).name;
  if (name) return String(name);
  const email = (row as { email?: string }).email;
  if (email) return String(email);
  return String(row.id).slice(0, 8) + "…";
}

function isUserResource(resource: string): boolean {
  return resource === "base/user" || resource.endsWith("/user");
}

interface Props {
  label: string;
  relation: string;
  value: string | null | undefined;
  onChange: (v: string | null) => void;
  required?: boolean;
  error?: string;
  readOnly?: boolean;
  /** From API `expand=` (`person_id__name`). Skips initial lookup. */
  initialLabel?: string;
}

/** Searchable FK: stores UUID, displays related record `name`. */
export default function Many2OneField({
  label, relation, value, onChange, required, error, readOnly, initialLabel,
}: Props) {
  const resource = relationToResource(relation);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [debounced] = useDebouncedValue(search, 200);
  const [options, setOptions] = useState<{ value: string; label: string }[]>([]);

  const loadOne = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/${resource}/${id}`, { skipGlobalErrorToast: true });
      const label = optionLabel(data as Record<string, unknown>);
      setOptions((prev) => {
        const map = new Map(prev.map((o) => [o.value, o]));
        map.set(id, { value: id, label });
        return Array.from(map.values());
      });
    } catch {
      setOptions((prev) => {
        const map = new Map(prev.map((o) => [o.value, o]));
        map.set(id, { value: id, label: String(id).slice(0, 8) + "…" });
        return Array.from(map.values());
      });
    } finally {
      setLoading(false);
    }
  }, [resource]);

  useEffect(() => {
    if (initialLabel && value) {
      setOptions((prev) => {
        const map = new Map(prev.map((o) => [o.value, o]));
        map.set(value, { value, label: initialLabel });
        return Array.from(map.values());
      });
    }
  }, [initialLabel, value]);

  useEffect(() => {
    if (value && initialLabel) return;
    if (value) void loadOne(value);
  }, [value, loadOne, initialLabel]);

  /** Preload recent rows so the dropdown is usable before the user types. */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/${resource}`, {
          params: { limit: 30 },
          skipGlobalErrorToast: true,
        });
        const items: Record<string, unknown>[] = data.items ?? data ?? [];
        const opts = items.map((row) => ({
          value: String(row.id),
          label: optionLabel(row),
        }));
        if (!cancelled) {
          setOptions((prev) => {
            const map = new Map<string, { value: string; label: string }>();
            for (const o of opts) map.set(o.value, o);
            if (value) {
              const cur = prev.find((p) => p.value === value);
              if (cur) map.set(cur.value, cur);
            }
            return Array.from(map.values());
          });
        }
      } catch {
        if (!cancelled) setOptions((prev) => (value ? prev : []));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [resource, value]);

  useEffect(() => {
    if (!debounced || debounced.length < 1) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const requests = [
          api.get(`/${resource}`, {
            params: { name__contains: debounced, limit: 30 },
            skipGlobalErrorToast: true,
          }),
        ];
        if (isUserResource(resource)) {
          requests.push(
            api.get(`/${resource}`, {
              params: { email__contains: debounced, limit: 30 },
              skipGlobalErrorToast: true,
            }),
          );
        }
        const responses = await Promise.all(requests);
        const items: Record<string, unknown>[] = [];
        for (const { data } of responses) {
          items.push(...(data.items ?? data ?? []));
        }
        const deduped = new Map<string, { value: string; label: string }>();
        for (const row of items) {
          const id = String(row.id);
          deduped.set(id, { value: id, label: optionLabel(row) });
        }
        if (!cancelled) {
          setOptions((prev) => {
            const map = new Map(deduped);
            if (value) {
              const cur = prev.find((p) => p.value === value);
              if (cur) map.set(cur.value, cur);
            }
            return Array.from(map.values());
          });
        }
      } catch {
        if (!cancelled) setOptions([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [debounced, resource, value]);

  const data = useMemo(() => options, [options]);

  if (readOnly) {
    const row = data.find((d) => d.value === value);
    return (
      <Text size="sm">
        <Text span fw={500} size="xs" c="dimmed" display="block" mb={4}>{label}</Text>
        {row?.label ?? (value ? String(value).slice(0, 8) + "…" : "—")}
      </Text>
    );
  }

  return (
    <Select
      label={label}
      required={required}
      error={error}
      placeholder={`Search ${label.toLowerCase()}…`}
      searchable
      clearable
      data={data}
      value={value || null}
      onChange={(v) => onChange(v)}
      onSearchChange={setSearch}
      rightSection={loading ? <Loader size="xs" /> : undefined}
      nothingFoundMessage="No matches"
    />
  );
}
