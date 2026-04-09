import { redirect } from "next/navigation";

export default function BusinessMediaPage({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/media`);
}
