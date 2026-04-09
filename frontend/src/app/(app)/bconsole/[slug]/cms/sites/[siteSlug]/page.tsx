import { redirect } from "next/navigation";

export default function BusinessCmsSiteDetailRedirect({
  params,
}: {
  params: { slug: string; siteSlug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites/${params.siteSlug}`);
}
