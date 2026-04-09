import { redirect } from "next/navigation";

export default function BusinessCmsPageEditorRedirect({
  params,
}: {
  params: { slug: string; siteSlug: string; pageSlug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites/${params.siteSlug}/pages/${params.pageSlug}`);
}
