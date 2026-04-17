"use client";
import { Group, UnstyledButton, Text } from "@mantine/core";

interface Props {
  label?: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  readOnly?: boolean;
}

/** Horizontal step control for status / enum fields (from XML widget="statusbar"). */
export default function StatusbarField({ label, value, options, onChange, readOnly }: Props) {
  return (
    <div>
      {label && (
        <Text size="xs" fw={600} c="dimmed" mb={6} tt="uppercase" style={{ letterSpacing: "0.06em" }}>
          {label}
        </Text>
      )}
      <Group gap={4} wrap="wrap">
        {options.map((opt) => {
          const active = opt.value === value;
          return (
            <UnstyledButton
              key={opt.value}
              type="button"
              disabled={readOnly}
              onClick={() => onChange(opt.value)}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--mantine-radius-sm)",
                border: `1px solid ${active ? "var(--mantine-color-blue-filled)" : "var(--mantine-color-default-border)"}`,
                background: active ? "var(--mantine-color-blue-light)" : "var(--mantine-color-body)",
              }}
            >
              <Text size="sm" fw={active ? 600 : 400}>
                {opt.label}
              </Text>
            </UnstyledButton>
          );
        })}
      </Group>
    </div>
  );
}
