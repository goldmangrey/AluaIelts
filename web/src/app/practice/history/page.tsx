import {HistoryPage} from '@/features/practice/history/pages';
export const metadata={title:'My Practice History'};
export default async function Page({searchParams}:{searchParams:Promise<{day?:string}>}){const {day}=await searchParams;return <HistoryPage day={day}/>;}
