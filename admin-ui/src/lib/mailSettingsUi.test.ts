import { describe, expect, it } from "vitest";
import { isPlaceholderSmtpHost, placeholderHostHintText } from "./mailSettingsUi";

describe("isPlaceholderSmtpHost", () => {
  it("detects test and example hosts", () => {
    expect(isPlaceholderSmtpHost("smtp.test.example")).toBe(true);
    expect(isPlaceholderSmtpHost("mail.example")).toBe(true);
    expect(isPlaceholderSmtpHost("localhost")).toBe(true);
  });

  it("allows real SMTP hosts", () => {
    expect(isPlaceholderSmtpHost("smtp.gmail.com")).toBe(false);
    expect(isPlaceholderSmtpHost("mail.company.com")).toBe(false);
  });
});

describe("placeholderHostHintText", () => {
  it("returns English fallback when catalog is missing the key", () => {
    const t = (key: string) => key;
    expect(placeholderHostHintText(t)).toContain("placeholder");
  });
});
