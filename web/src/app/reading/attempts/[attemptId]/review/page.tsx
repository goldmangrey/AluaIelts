import { notFound } from "next/navigation";
import { RecordsPage } from "@/features/reading/exam/records-page";
export default async function Page({params,searchParams}:{params:Promise<{attemptId:string}>;searchParams:Promise<{question?:string|string[]}>}) {
 const {attemptId}=await params;
 if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(attemptId))notFound();
 const {question}=await searchParams;
 return <RecordsPage id={attemptId} review reviewQuestionId={typeof question==="string"?question:undefined}/>;
}
