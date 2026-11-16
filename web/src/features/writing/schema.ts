/** Groq constrained decoding schema: only types, objects, arrays, enums and nullable unions. */
const string={type:'string'};
const object=(properties:Record<string,unknown>)=>({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
const improvement={anyOf:[object({candidate_id:string,action:string}),{type:'null'}]};
const criterion=object({strength:string,limitation:{type:['string','null']},descriptor_fit:string,evidence:{type:'array',items:string},band:{type:'number'},improvement});
export const writingSchema=object({criteria:object({task_response:criterion,coherence_cohesion:criterion,lexical_resource:criterion,grammar:criterion}),issues:{type:'array',items:object({candidate_id:string,original:string,correction:string,category:{type:'string',enum:['grammar_error','lexical_error']},why:string})}});
