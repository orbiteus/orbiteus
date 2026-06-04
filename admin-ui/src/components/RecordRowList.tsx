"use client";

import Link from "next/link";
import { ActionIcon, Box, Group, Menu, Text } from "@mantine/core";
import {
  IconChevronRight,
  IconDots,
  IconSortAscending,
  IconSortDescending,
  IconTrash,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import classes from "./RecordRowList.module.css";

export type RecordRowColumn = {
  key: string;
  label: string;
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
};

type RecordRowListProps = {
  rows: Record<string, unknown>[];
  columns: RecordRowColumn[];
  editHref?: (id: string) => string;
  onDelete: (id: string) => void;
  onRowHover?: (id: string) => void;
  orderBy?: string | null;
  orderDir?: "asc" | "desc" | null;
  onSort?: (key: string) => void;
};

function renderCell(
  column: RecordRowColumn,
  row: Record<string, unknown>,
): React.ReactNode {
  const value = row[column.key];
  if (column.render) return column.render(value, row);
  if (value == null || value === "") return "—";
  return String(value);
}

function gridTemplate(columnCount: number): string {
  const dataCols = Math.max(columnCount, 1);
  const flexible = Array.from({ length: dataCols - 1 }, () => "minmax(72px, 1fr)").join(" ");
  return flexible
    ? `minmax(140px, 2.2fr) ${flexible} 32px`
    : "minmax(140px, 1fr) 32px";
}

export default function RecordRowList({
  rows,
  columns,
  editHref,
  onDelete,
  onRowHover,
  orderBy,
  orderDir,
  onSort,
}: RecordRowListProps) {
  const t = useT();
  const template = gridTemplate(columns.length);
  const primaryKey = columns[0]?.key;

  return (
    <div className={classes.panel}>
      <div className={classes.header} style={{ gridTemplateColumns: template }}>
        {columns.map((column) => (
          <Box
            key={column.key}
            component={onSort ? "button" : "div"}
            type={onSort ? "button" : undefined}
            className={onSort ? classes.headerButton : undefined}
            onClick={onSort ? () => onSort(column.key) : undefined}
          >
            <Group gap={4} wrap="nowrap">
              <span className={classes.headerLabel}>{column.label}</span>
              {onSort && orderBy === column.key && (
                orderDir === "desc"
                  ? <IconSortDescending size={11} color="var(--mantine-color-dark-6)" />
                  : <IconSortAscending size={11} color="var(--mantine-color-dark-6)" />
              )}
            </Group>
          </Box>
        ))}
        <span />
      </div>

      {rows.map((row) => {
        const id = String(row.id);
        const href = editHref?.(id);

        const rowInner = (
          <>
            {columns.map((column) => (
              <Text
                key={column.key}
                lineClamp={1}
                className={column.key === primaryKey ? classes.primaryCell : classes.secondaryCell}
                component="div"
              >
                {renderCell(column, row)}
              </Text>
            ))}
            <div
              className={classes.actions}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
              }}
            >
              <Menu position="bottom-end" withinPortal>
                <Menu.Target>
                  <ActionIcon variant="subtle" color="gray" size="sm" aria-label={t("recordRow.actions")}>
                    <IconDots size={14} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Item
                    color="red"
                    leftSection={<IconTrash size={14} />}
                    onClick={() => onDelete(id)}
                  >
                    {t("common.delete")}
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
              {href && (
                <IconChevronRight size={13} color="var(--mantine-color-gray-5)" />
              )}
            </div>
          </>
        );

        if (!href) {
          return (
            <div key={id} className={classes.row} style={{ gridTemplateColumns: template }}>
              {rowInner}
            </div>
          );
        }

        return (
          <Link
            key={id}
            href={href}
            className={`${classes.row} ${classes.rowInteractive}`}
            style={{ gridTemplateColumns: template }}
            onMouseEnter={() => onRowHover?.(id)}
            onFocus={() => onRowHover?.(id)}
          >
            {rowInner}
          </Link>
        );
      })}
    </div>
  );
}
