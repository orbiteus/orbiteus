import adminPackage from "../../package.json";
import i18nPackage from "../../../packages/i18n/package.json";
import portalPackage from "../../../portal-ui/package.json";

/** Workspace package versions shown on Technical → System status. */
export const FRONTEND_STACK_VERSIONS = {
  adminUi: String(adminPackage.version ?? "?"),
  portalUi: String(portalPackage.version ?? "?"),
  i18n: String(i18nPackage.version ?? "?"),
  next: String(adminPackage.dependencies?.next ?? "?"),
  react: String(adminPackage.dependencies?.react ?? "?"),
  mantine: String(adminPackage.dependencies?.["@mantine/core"] ?? "?"),
  reactQuery: String(adminPackage.dependencies?.["@tanstack/react-query"] ?? "?"),
} as const;
