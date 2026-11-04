import {notFound} from "next/navigation";
import {ListeningPage} from "@/features/listening/pages";
export default async function Page({params}:{params:Promise<{attemptId:string}>}){const {attemptId}=await params;if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(attemptId))notFound();return <ListeningPage kind="result" id={attemptId}/>;}
