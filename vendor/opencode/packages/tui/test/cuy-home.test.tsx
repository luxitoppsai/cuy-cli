import { expect, mock, test } from "bun:test"
import { createTestRenderer } from "@opentui/core/testing"
import { Effect } from "effect"
import { AppNodeBuilder } from "@opencode-ai/core/effect/app-node-builder"
import { Global } from "@opencode-ai/core/global"
import { createTuiResolvedConfig } from "./fixture/tui-runtime"
import { createEventSource, createFetch, directory } from "./fixture/tui-sdk"

test("home explains configuration and next action without claiming a live connection", async () => {
  const setup = await createTestRenderer({ width: 100, height: 36, useThread: false, useMouse: true })
  const core = await import("@opentui/core")
  mock.module("@opentui/core", () => ({ ...core, createCliRenderer: async () => setup.renderer }))
  const events = createEventSource()
  const calls = createFetch()
  const { run } = await import("../src/app")
  const task = Effect.runPromise(run({
    url: "http://test", directory, config: createTuiResolvedConfig({ plugin_enabled: {} }),
    fetch: calls.fetch, events: events.source, args: {},
    pluginHost: { async start() {}, async dispose() {} },
  }).pipe(Effect.provide(AppNodeBuilder.build(Global.node))))
  try {
    for (let i = 0; i < 100; i++) {
      await new Promise((resolve) => setTimeout(resolve, 25))
      await setup.renderOnce()
      if (setup.captureCharFrame().includes("/empezar")) break
    }
    const frame = setup.captureCharFrame()
    if (process.env.CUY_UI_CAPTURE) await Bun.write(process.env.CUY_UI_CAPTURE, frame)
    expect(frame).toContain("Databricks Model Serving")
    expect(frame).toContain("/empezar")
    expect(frame).toContain("Sin workspace configurado")
    expect(frame).not.toContain("Conectado")
    const requests = calls.session.length
    const row = frame.split("\n").findIndex((line) => line.includes("/empezar"))
    await setup.mockMouse.click(18, row)
    await setup.waitForFrame((text) => text.includes("¿Qué querés hacer?"))
    expect(setup.captureCharFrame()).toContain("¿Qué querés hacer?")
    expect(setup.captureCharFrame()).toContain("Entender el proyecto")
    expect(calls.session.length).toBe(requests)
    setup.mockInput.pressEnter()
    await setup.renderOnce()
    setup.resize(64, 24)
    await setup.renderOnce()
    const compact = setup.captureCharFrame()
    expect(compact).toContain("/empezar")
    expect(compact).not.toContain("Límite mensual")
    if (process.env.CUY_UI_CAPTURE) await Bun.write(process.env.CUY_UI_CAPTURE + ".compact", compact)
  } finally {
    process.emit("SIGHUP")
    await task
    if (!setup.renderer.isDestroyed) setup.renderer.destroy()
    mock.restore()
  }
})
