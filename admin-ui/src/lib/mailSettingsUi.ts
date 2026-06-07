/** Hostnames used in tests / docs — connection probes are expected to fail. */
const PLACEHOLDER_HOST_PATTERNS = [
  /\.example$/i,
  /^smtp\.test\./i,
  /^localhost$/i,
  /^127\.0\.0\.1$/i,
];

/** User-visible copy when the API catalog is stale or missing a new key. */
export const PLACEHOLDER_SMTP_HOST_HINT =
  "This host looks like a placeholder (e.g. smtp.test.example). Replace it with your real SMTP server before testing the connection.";

export function placeholderHostHintText(t: (key: string) => string): string {
  const msg = t("mail.placeholderHostHint");
  return msg === "mail.placeholderHostHint" ? PLACEHOLDER_SMTP_HOST_HINT : msg;
}

export function isPlaceholderSmtpHost(host: string): boolean {
  const trimmed = host.trim();
  if (!trimmed) return false;
  return PLACEHOLDER_HOST_PATTERNS.some((re) => re.test(trimmed));
}
