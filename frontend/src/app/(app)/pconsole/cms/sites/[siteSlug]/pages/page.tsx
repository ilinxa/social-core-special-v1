import { redirect } from "next/navigation";

export default function PlatformCmsPagesRedirect({
  params,
}: {
  params: { siteSlug: string };
}) {
  redirect(`/cconsole/sites/${params.siteSlug}`);
}
