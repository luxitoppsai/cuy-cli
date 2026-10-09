import { createHash } from "node:crypto"
import { Effect } from "effect"
import { FSUtil } from "@opencode-ai/core/fs-util"

/** Revalidate the bytes used to prepare an edit after permission approval. */
export const assertVersion = Effect.fn("FileVersion.assertVersion")(function* (
  fs: FSUtil.Interface,
  filePath: string,
  expected: string | null,
) {
  const current = yield* fs.readFile(filePath).pipe(
    Effect.map((bytes) => createHash("sha256").update(bytes).digest("hex")),
    Effect.catchReason("PlatformError", "NotFound", () => Effect.succeed(null)),
  )
  if (current === expected) return
  return yield* Effect.fail(
    new Error(`File changed while preparing the edit: ${filePath}. Read the file again before retrying.`),
  )
})
