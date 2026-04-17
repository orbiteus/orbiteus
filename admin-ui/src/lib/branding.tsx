"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

export interface Branding {
  name: string;
  logo_url: string;
  favicon_url: string;
}

const DEFAULT: Branding = {
  name: process.env.NEXT_PUBLIC_APP_NAME ?? "Orbiteus",
  logo_url: process.env.NEXT_PUBLIC_APP_LOGO_URL ?? "",
  favicon_url: process.env.NEXT_PUBLIC_APP_FAVICON_URL ?? "",
};

const BrandingContext = createContext<Branding>(DEFAULT);

export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const [branding, setBranding] = useState<Branding>(DEFAULT);

  useEffect(() => {
    api.get("/base/branding")
      .then(({ data }) => setBranding({
        name: data.name || DEFAULT.name,
        logo_url: data.logo_url || DEFAULT.logo_url,
        favicon_url: data.favicon_url || DEFAULT.favicon_url,
      }))
      .catch(() => {/* keep defaults */});
  }, []);

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
