import { redirect } from "next/navigation";

export default function BusinessCmsCatalogRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/catalog`);
}
