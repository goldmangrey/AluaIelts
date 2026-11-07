import {ApiError} from "@/lib/api/client";
/** Only explicit validation rejection is known not to have finalized an attempt. */
export function rejectedSubmit(error:unknown):error is ApiError {
 return error instanceof ApiError&&error.status===422&&["validation_error","request_validation_error"].includes(error.code);
}
