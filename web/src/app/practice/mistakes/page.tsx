import {Suspense} from 'react';
import {MistakesPage} from '@/features/practice/history/mistakes-page';
export const metadata={title:'My Mistakes'};
export default function Page(){return <Suspense fallback={<p role="status">Loading your mistakes…</p>}><MistakesPage/></Suspense>;}
