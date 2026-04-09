import { redirect } from "next/navigation";

export default function BusinessContentPage({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/sites`);
}
