import {NextRequest} from "next/server";
import {audioProxy} from "@/features/listening/audio-proxy";
export const dynamic="force-dynamic";
async function proxy(request:NextRequest,{params}:{params:Promise<{attemptId:string;part:string}>}){const {attemptId,part}=await params;return audioProxy(request,attemptId,part);}
export {proxy as GET,proxy as HEAD};
