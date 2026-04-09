import { redirect } from "next/navigation";

export default function BusinessCmsSitesRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites`);
}
