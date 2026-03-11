"use client";

import { useParams } from "next/navigation";

import { TransactionDetailPage } from "@/features/transactions/components/TransactionDetailPage";

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();

  return <TransactionDetailPage transactionId={id} basePath="/activity" />;
}
