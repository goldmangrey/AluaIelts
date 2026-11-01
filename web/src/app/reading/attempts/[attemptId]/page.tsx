import { notFound } from "next/navigation";
import { AttemptPage } from "@/features/reading/exam/attempt-page";
export const metadata = { title: "Reading test" };
export default async function Page({ params }: { params: Promise<{ attemptId: string }> }) {
  const { attemptId } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(attemptId)) notFound();
  return <AttemptPage id={attemptId} />;
}
