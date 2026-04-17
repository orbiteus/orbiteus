import { redirect } from "next/navigation";

export default function LegacyPipelinesListRedirect() {
  redirect("/crm/pipeline");
}
