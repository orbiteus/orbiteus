import type { Metadata } from "next";
import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";
import { QueryProvider } from "@/components/QueryProvider";
import PortalI18nShell from "@/components/PortalI18nShell";
import { orbiteusTheme } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Orbiteus Portal",
  description: "External partner portal for shared resources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-mantine-color-scheme="light" suppressHydrationWarning>
      <body>
        <MantineProvider theme={orbiteusTheme} defaultColorScheme="light">
          <QueryProvider>
            <PortalI18nShell>{children}</PortalI18nShell>
          </QueryProvider>
        </MantineProvider>
      </body>
    </html>
  );
}
