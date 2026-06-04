import { redirect } from "next/navigation";

/** Legacy URL — Roles CRUD lives on the schema-driven base.role screen. */
export default function UsersRolesRedirectPage() {
  redirect("/base/role");
}
