import type { Metadata } from "next";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/dates/styles.css";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import AppShellLayout from "@/components/AppShellLayout";
import AdminI18nShell from "@/components/AdminI18nShell";
import { QueryProvider } from "@/components/QueryProvider";
import { BrandingProvider } from "@/lib/branding";
import { AuthProvider } from "@/lib/auth";
import { orbiteusTheme } from "@/lib/theme";

export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_APP_NAME ?? "Orbiteus",
  description: "Composable ERP Engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-mantine-color-scheme="light" suppressHydrationWarning>
      <body>
        <MantineProvider theme={orbiteusTheme} defaultColorScheme="light">
          <Notifications />
          <QueryProvider>
            <BrandingProvider>
              <AuthProvider>
                <AdminI18nShell>
                  <AppShellLayout>{children}</AppShellLayout>
                </AdminI18nShell>
              </AuthProvider>
            </BrandingProvider>
          </QueryProvider>
        </MantineProvider>
      </body>
    </html>
  );
}
