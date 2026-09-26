import { isRecord } from "@/util/record"

/** Per-response extractor: cache and reasoning fields are top-level on Databricks. */
export function databricksUsage(body: unknown): Record<string, number> {
  if (!isRecord(body) || !isRecord(body.usage)) return {}
  const result: Record<string, number> = {}
  for (const [source, target] of Object.entries({
    cache_read_input_tokens: "cacheReadInputTokens",
    cache_creation_input_tokens: "cacheWriteInputTokens",
    reasoning_tokens: "reasoningTokens",
  })) {
    const value = body.usage[source]
    if (typeof value === "number" && Number.isFinite(value) && value >= 0) result[target] = value
  }
  return result
}

export const databricksMetadata = {
  extractMetadata: async ({ parsedBody }: { parsedBody: unknown }) => ({ cuyDatabricks: databricksUsage(parsedBody) }),
  createStreamExtractor() {
    const usage: Record<string, number> = {}
    return {
      processChunk(chunk: unknown) { Object.assign(usage, databricksUsage(chunk)) },
      buildMetadata() { return { cuyDatabricks: usage } },
    }
  },
}
