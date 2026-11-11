import {WritingPage} from '@/features/writing/pages';
export const metadata={title:'Writing Task 2'};
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return <WritingPage kind="editor" id={id}/>;}
