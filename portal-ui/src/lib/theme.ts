import { createTheme, type MantineColorsTuple } from "@mantine/core";

/** Shared with admin-ui — cool zinc / charcoal default palette. */
export const ORBITEUS_DARK: MantineColorsTuple = [
  "#fafafa",
  "#f4f4f5",
  "#e4e4e7",
  "#d4d4d8",
  "#a1a1aa",
  "#71717a",
  "#52525b",
  "#3f3f46",
  "#27272a",
  "#09090b",
];

/** Same balanced density tokens as admin-ui (docs/10-design-system.md). */
export const orbiteusTheme = createTheme({
  primaryColor: "dark",
  colors: {
    dark: ORBITEUS_DARK,
  },
  primaryShade: { light: 8, dark: 1 },
  fontFamily: "Inter, system-ui, sans-serif",
  defaultRadius: "md",
  spacing: { xs: "8px", sm: "12px", md: "16px", lg: "22px", xl: "32px" },
  fontSizes: {
    xs: "12px",
    sm: "14px",
    md: "16px",
    lg: "18px",
    xl: "20px",
  },
  lineHeights: {
    xs: "1.4",
    sm: "1.45",
    md: "1.5",
    lg: "1.55",
    xl: "1.6",
  },
  headings: {
    fontFamily: "Inter, system-ui, sans-serif",
    fontWeight: "600",
    sizes: {
      h1: { fontSize: "1.875rem", lineHeight: "1.25" },
      h2: { fontSize: "1.5rem", lineHeight: "1.3" },
      h3: { fontSize: "1.25rem", lineHeight: "1.35" },
      h4: { fontSize: "1.125rem", lineHeight: "1.4" },
    },
  },
  components: {
    Paper: {
      defaultProps: { radius: "md", withBorder: true, p: "md" },
    },
    Button: {
      defaultProps: { radius: "md", fw: 500, size: "sm" },
    },
    TextInput: {
      defaultProps: { radius: "md", size: "sm" },
    },
    Textarea: {
      defaultProps: { radius: "md", size: "sm", minRows: 3 },
    },
  },
});
