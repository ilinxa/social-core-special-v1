import { redirect } from "next/navigation";

export default function BusinessCmsLibraryRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/library`);
}
