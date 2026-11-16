import {notFound, redirect} from "next/navigation";
import {matchesExamBook, parseBook} from "@/features/reading/routes";
export default async function Test({params}:{params:Promise<{book:string;examId:string}>}) {
  const {book,examId}=await params, number=parseBook(book);
  if(!number||!matchesExamBook(examId,number))notFound();
  redirect(`/reading/${book}?test=${encodeURIComponent(examId)}`);
}
