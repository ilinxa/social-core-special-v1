import { redirect } from "next/navigation";

export default function BusinessCmsPage({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites`);
}
