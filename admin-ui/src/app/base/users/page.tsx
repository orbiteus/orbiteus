import { redirect } from "next/navigation";

export default function LegacyUsersRedirect() {
  redirect("/base/user");
}
