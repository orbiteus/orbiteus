import type { Metadata } from "next";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/dates/styles.css";
import { ColorSchemeScript, MantineProvider, createTheme } from "@mantine/core";
import { DatesProvider } from "@mantine/dates";
import { Notifications } from "@mantine/notifications";
import AppShellLayout from "@/components/AppShellLayout";
import { BrandingProvider } from "@/lib/branding";

export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_APP_NAME ?? "Orbiteus",
  description: "Composable ERP Engine",
};

const theme = createTheme({
  primaryColor: "blue",
  fontFamily: "Inter, system-ui, sans-serif",
  defaultRadius: "sm",
  defaultGradient: { from: "blue.6", to: "cyan.5", deg: 120 },
  colors: {
    dark: [
      "#C1C2C5",
      "#A6A7AB",
      "#909296",
      "#5c5f66",
      "#373A40",
      "#2C2E33",
      "#25262b",
      "#1A1B1E",
      "#141517",
      "#101113",
    ],
  },
  headings: {
    fontFamily: "Inter, system-ui, sans-serif",
  },
  components: {
    Paper: {
      defaultProps: { radius: "md", withBorder: true, p: "md" },
      styles: {
        root: {
          borderColor: "var(--mantine-color-default-border)",
          background: "var(--mantine-color-body)",
          boxShadow: "0 1px 2px rgba(15,23,42,0.04)",
        },
      },
    },
    Button: {
      defaultProps: { radius: "md", fw: 600 },
    },
    TextInput: {
      defaultProps: { radius: "md" },
    },
    Table: {
      defaultProps: { verticalSpacing: "sm", horizontalSpacing: "md" },
    },
    SegmentedControl: {
      defaultProps: { radius: "md" },
    },
  },
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ColorSchemeScript defaultColorScheme="light" />
      </head>
      <body>
        <MantineProvider theme={theme} defaultColorScheme="light">
          <DatesProvider settings={{ locale: "en", firstDayOfWeek: 1 }}>
            <Notifications />
            <BrandingProvider>
              <AppShellLayout>{children}</AppShellLayout>
            </BrandingProvider>
          </DatesProvider>
        </MantineProvider>
      </body>
    </html>
  );
}
