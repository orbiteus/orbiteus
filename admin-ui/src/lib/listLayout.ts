export type ListColumn = {
  key: string;
  label: string;
};

const PRIMARY_KEYS = ["name", "title", "email", "slug", "label"];

export function pickPrimaryColumn(columns: ListColumn[]): ListColumn | null {
  if (columns.length === 0) return null;
  const preferred = columns.find((col) => PRIMARY_KEYS.includes(col.key));
  return preferred ?? columns[0];
}

export function secondaryColumns(columns: ListColumn[], primaryKey: string | null): ListColumn[] {
  return columns.filter((col) => col.key !== primaryKey).slice(0, 5);
}
