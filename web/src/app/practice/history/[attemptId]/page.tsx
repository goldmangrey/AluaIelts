import {notFound} from 'next/navigation';
import {HistoryDetail} from '@/features/practice/history/pages';
export const metadata={title:'Saved practice result'};
export default async function Page({params}:{params:Promise<{attemptId:string}>}){
 const {attemptId}=await params;if(!/^[0-9a-f-]{36}$/i.test(attemptId))notFound();return <HistoryDetail attemptId={attemptId}/>;
}
