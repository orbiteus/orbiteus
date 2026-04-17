import { redirect } from "next/navigation";

export default function LegacyCompaniesRedirect() {
  redirect("/base/company");
}
