import { expect, test } from "bun:test"
import { createOpenAICompatible } from "@ai-sdk/openai-compatible"
import { databricksMetadata, databricksUsage } from "../../src/provider/databricks-usage"
import { Session } from "../../src/session/session"
import type { Provider } from "../../src/provider/provider"
import { Usage } from "@opencode-ai/llm"

test("Databricks usage survives the SDK and cache/reasoning are priced exactly once", async () => {
  const chunks = [
    { choices: [{ index: 0, delta: { content: "ok" }, finish_reason: null }], usage: { prompt_tokens: 1000, completion_tokens: null, cache_read_input_tokens: 600 } },
    { choices: [{ index: 0, delta: {}, finish_reason: "stop" }], usage: { prompt_tokens: 1000, completion_tokens: 100, cache_read_input_tokens: 600, cache_creation_input_tokens: 200, reasoning_tokens: 20 } },
  ]
  const sdk = createOpenAICompatible({ name: "cuy", baseURL: "https://workspace.example/serving-endpoints", metadataExtractor: databricksMetadata,
    fetch: Object.assign(async () => new Response(chunks.map((c) => `data: ${JSON.stringify(c)}\n\n`).join("") + "data: [DONE]\n\n", { headers: { "content-type": "text/event-stream" } }), { preconnect() {} }),
  })
  const result = await sdk.chatModel("modelo").doStream({ prompt: [{ role: "user", content: [{ type: "text", text: "hi" }] }] })
  let seen = false
  const reader = result.stream.getReader()
  while (true) {
    const { done, value: part } = await reader.read()
    if (done) break
    if (part.type === "error") throw part.error
    if (part.type !== "finish") continue
    seen = true
    const priced = Session.getUsage({
      model: { cost: { input: 3, output: 15, cache: { read: 0.3, write: 3.75 } } } as Provider.Model,
      usage: new Usage({ inputTokens: part.usage.inputTokens.total, outputTokens: part.usage.outputTokens.total }),
      metadata: part.providerMetadata,
    })
    expect(priced.tokens.input).toBe(200)
    expect(priced.tokens.cache).toEqual({ read: 600, write: 200 })
    expect(priced.tokens.output).toBe(80)
    expect(priced.tokens.reasoning).toBe(20)
    expect(priced.cost).toBeCloseTo(0.00303, 10)
  }
  expect(seen).toBe(true)
})

test("extractors isolate requests and ignore null or invalid usage", () => {
  const first = databricksMetadata.createStreamExtractor()
  const second = databricksMetadata.createStreamExtractor()
  first.processChunk({ usage: { cache_read_input_tokens: 600 } })
  first.processChunk({ usage: { cache_read_input_tokens: null } })
  expect(first.buildMetadata().cuyDatabricks.cacheReadInputTokens).toBe(600)
  expect(second.buildMetadata().cuyDatabricks).toEqual({})
  expect(databricksUsage({ usage: { reasoning_tokens: -1, cache_creation_input_tokens: "100" } })).toEqual({})
})
