import dayjs from "dayjs";

export function formatListDate(value: unknown): string {
  if (value == null || value === "") return "—";
  const s = String(value);
  const d = dayjs(s);
  if (!d.isValid()) return s;
  return d.format("YYYY-MM-DD HH:mm");
}

export function formatMoney(value: unknown, currency = "PLN"): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(n);
}

export function displayMany2oneCell(row: Record<string, unknown>, key: string): string {
  const name = row[`${key}__name`] ?? row[`${key}__display`];
  if (name != null && String(name) !== "") return String(name);
  const id = row[key];
  if (id != null && String(id) !== "") return String(id).slice(0, 8) + "…";
  return "—";
}
