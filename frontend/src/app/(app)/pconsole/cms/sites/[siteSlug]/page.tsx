import { redirect } from "next/navigation";

export default function PlatformCmsSiteDetailRedirect({
  params,
}: {
  params: { siteSlug: string };
}) {
  redirect(`/cconsole/sites/${params.siteSlug}`);
}
