import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { ReactElement } from "react";
import { MantineProvider } from "@mantine/core";
import { I18nProvider } from "@orbiteus/i18n";
import { LastLoginCell } from "./LastLoginCell";

const CATALOGS = {
  en: { "common.never": "Never" },
  pl: { "common.never": "Nigdy" },
};

function render(cell: ReactElement, language = "en") {
  return renderToStaticMarkup(
    <I18nProvider
      userLanguage={language}
      runtimeOverrides={CATALOGS}
      waitForCatalog={false}
    >
      <MantineProvider>{cell}</MantineProvider>
    </I18nProvider>,
  );
}

describe("LastLoginCell", () => {
  it("shows Never when last login is empty", () => {
    const html = render(<LastLoginCell lastLogin={null} device={null} />);
    expect(html).toContain("Never");
  });

  it("renders Polish never label", () => {
    const html = render(<LastLoginCell lastLogin={null} device={null} />, "pl");
    expect(html).toContain("Nigdy");
  });

  it("renders formatted date for desktop login", () => {
    const html = render(
      <LastLoginCell lastLogin="2026-05-29T12:30:00Z" device="desktop" />,
    );
    expect(html).toContain("2026-05-29");
  });
});
