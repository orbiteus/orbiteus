import { redirect } from "next/navigation";

export default function LegacyCustomersListRedirect() {
  redirect("/crm/customer");
}
