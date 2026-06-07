/** When the authenticated admin shell must stay on the loading gate. */
export function shouldBlockAuthenticatedShell(opts: {
  isPublicRoute: boolean;
  hydrated: boolean;
  hasCatalog: boolean;
}): boolean {
  if (opts.isPublicRoute) return false;
  if (!opts.hydrated) return true;
  return !opts.hasCatalog;
}
