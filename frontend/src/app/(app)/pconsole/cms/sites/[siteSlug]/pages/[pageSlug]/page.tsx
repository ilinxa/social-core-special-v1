import { redirect } from "next/navigation";

export default function PlatformCmsPageEditorRedirect({
  params,
}: {
  params: { siteSlug: string; pageSlug: string };
}) {
  redirect(`/cconsole/sites/${params.siteSlug}/pages/${params.pageSlug}`);
}
