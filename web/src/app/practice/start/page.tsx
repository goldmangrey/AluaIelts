import {Suspense} from 'react';
import {PageShell} from '@/components/page-shell';
import {StartPractice} from '@/features/guest/start';
export default function Page(){return <PageShell><Suspense fallback={<p role="status">Loading practice…</p>}><StartPractice/></Suspense></PageShell>}
