import { redirect } from "next/navigation";

export default function BusinessCmsApiKeysRedirect({
  params,
}: {
  params: { slug: string };
}) {
  redirect(`/cconsole/${params.slug}/api-keys`);
}
