import { ApiError } from "./api/client";

/** Bounds SDK initialization as well as network operations; always clears timer. */
export async function withTimeout<T>(operation: Promise<T>, milliseconds = 15_000): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([operation, new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new ApiError(0, "timeout")), milliseconds);
    })]);
  } finally { clearTimeout(timer); }
}
