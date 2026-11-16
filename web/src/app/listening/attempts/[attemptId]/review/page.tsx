import {notFound} from "next/navigation";
import {ListeningPage} from "@/features/listening/pages";
export default async function Page({params,searchParams}:{params:Promise<{attemptId:string}>;searchParams:Promise<{question?:string}>}){const {attemptId}=await params;if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(attemptId))notFound();const question=Number((await searchParams).question);return <ListeningPage kind="review" id={attemptId} reviewQuestion={Number.isInteger(question)&&question>=1&&question<=40?question:undefined}/>;}
