import { redirect } from "next/navigation";

export default function BusinessCmsMediaRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/media`);
}
