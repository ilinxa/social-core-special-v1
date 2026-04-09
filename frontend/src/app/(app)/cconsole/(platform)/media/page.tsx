"use client";

import { MediaLibraryPage } from "@/features/cms/components/MediaLibraryPage";

export default function PlatformCmsMediaPage() {
  return <MediaLibraryPage context={{ type: "platform" }} />;
}
