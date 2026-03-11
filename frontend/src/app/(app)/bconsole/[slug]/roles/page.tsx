import { redirect } from "next/navigation";

export default function RolesPage({ params }: { params: { slug: string } }) {
  redirect(`/bconsole/${params.slug}/members`);
}
