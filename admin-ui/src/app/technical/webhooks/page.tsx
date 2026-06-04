import { redirect } from "next/navigation";

/** Legacy URL — webhooks live under Connectivity. */
export default function TechnicalWebhooksRedirectPage() {
  redirect("/connectivity/webhooks");
}
