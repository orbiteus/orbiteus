import { redirect } from "next/navigation";

export default function LegacyOpportunityEditRedirect({ params }: { params: { id: string } }) {
  redirect(`/crm/opportunity/${params.id}`);
}
