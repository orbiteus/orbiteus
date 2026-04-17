import { redirect } from "next/navigation";

export default function LegacyTechnicalAccessRedirect() {
  redirect("/base/ir-model-access");
}
