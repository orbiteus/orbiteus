import { redirect } from "next/navigation";

export default function LegacyCustomerNewRedirect() {
  redirect("/crm/customer/new");
}
