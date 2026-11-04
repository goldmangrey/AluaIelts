import {notFound} from "next/navigation";
import {SiteHeader} from "@/components/site-header";
import {ListeningPage} from "@/features/listening/pages";
export default async function Page({params}:{params:Promise<{book:string;examId:string}>}){const {book,examId}=await params;const match=/^cambridge-(0[4-9]|1[0-9]|2[01])-test-0[1-8]$/.exec(examId);if(!match||Number(book)!==Number(match[1]))notFound();return <><SiteHeader/><ListeningPage kind="prepare" id={examId}/></>;}
