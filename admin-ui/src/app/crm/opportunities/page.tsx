import { redirect } from "next/navigation";

export default function LegacyOpportunitiesListRedirect() {
  redirect("/crm/opportunity");
}
