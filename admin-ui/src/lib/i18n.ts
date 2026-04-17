"use client";

import { useMemo } from "react";

type Locale = "en" | "pl";

const MESSAGES: Record<Locale, Record<string, string>> = {
  en: {
    chart_by: "Chart by {field}",
    no_chart_data: "No data to chart. Ensure {rowField} and {measureField} are set on records.",
    calendar_by: "Calendar by {field}",
    month: "Month",
    week: "Week",
    day: "Day",
    today: "Today",
    filter_events: "Filter events…",
    events: "{count} events",
    no_events: "No events",
    no_events_on_selected_day: "No events on selected day.",
    events_list: "Events list",
    selected_day: "Selected day: {date}",
    filtered_period: "Filtered period: {period}",
    agenda: "Agenda",
    no_records_for_period: "No records for selected period.",
  },
  pl: {
    chart_by: "Wykres wg {field}",
    no_chart_data: "Brak danych do wykresu. Upewnij sie, ze pola {rowField} i {measureField} sa ustawione w rekordach.",
    calendar_by: "Kalendarz wg {field}",
    month: "Miesiac",
    week: "Tydzien",
    day: "Dzien",
    today: "Dzis",
    filter_events: "Filtruj wydarzenia…",
    events: "{count} wydarzen",
    no_events: "Brak wydarzen",
    no_events_on_selected_day: "Brak wydarzen w wybranym dniu.",
    events_list: "Lista wydarzen",
    selected_day: "Wybrany dzien: {date}",
    filtered_period: "Filtrowany okres: {period}",
    agenda: "Agenda",
    no_records_for_period: "Brak rekordow dla wybranego okresu.",
  },
};

function detectLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const forced = window.localStorage.getItem("locale");
  if (forced === "pl" || forced === "en") return forced;
  return navigator.language.toLowerCase().startsWith("pl") ? "pl" : "en";
}

export function useI18n() {
  const locale = useMemo(detectLocale, []);
  const dict = MESSAGES[locale] ?? MESSAGES.en;

  function t(key: string, vars?: Record<string, string | number>): string {
    let msg = dict[key] ?? MESSAGES.en[key] ?? key;
    if (!vars) return msg;
    for (const [k, v] of Object.entries(vars)) {
      msg = msg.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    }
    return msg;
  }

  return { locale, t };
}

export function humanizeFieldName(field: string): string {
  return field
    .replace(/_id$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

