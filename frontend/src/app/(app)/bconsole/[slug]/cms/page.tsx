import { redirect } from "next/navigation";

export default function BusinessCmsRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites`);
}
