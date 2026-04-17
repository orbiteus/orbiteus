import { redirect } from "next/navigation";

export default function LegacyCustomerEditRedirect({ params }: { params: { id: string } }) {
  redirect(`/crm/customer/${params.id}`);
}
