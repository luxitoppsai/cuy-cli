import { CuyOverview } from "../component/cuy-overview"
import { starters } from "../util/cuy"
import { useTheme } from "../context/theme"
import { useBindings } from "../keymap"
import { useDialog } from "../ui/dialog"
import { DialogSelect } from "../ui/dialog-select"
import { Prompt, type PromptRef } from "../component/prompt"
import { Show, createEffect, createMemo, createSignal, onMount } from "solid-js"
import { Logo } from "../component/logo"
import { useSync } from "../context/sync"
import { Toast } from "../ui/toast"
import { useArgs } from "../context/args"
import { useRouteData } from "../context/route"
import { usePromptRef } from "../context/prompt"
import { useLocal } from "../context/local"
import { usePluginRuntime } from "../plugin/runtime"
import { useEditorContext } from "../context/editor"
import { useTerminalDimensions } from "@opentui/solid"
import { useTuiConfig } from "../config"
import { HomeSessionDestinationProvider } from "./home/session-destination"

let once = false
const placeholder = {
  normal: ["¿Qué querés resolver en este proyecto?", "Explicame cómo funciona este proyecto", "Revisá este error y proponé una solución"],
  shell: ["ls -la", "git status", "pwd"],
}

export function Home() {
  const { theme } = useTheme()
  const dialog = useDialog()
  const pluginRuntime = usePluginRuntime()
  const sync = useSync()
  const route = useRouteData("home")
  const promptRef = usePromptRef()
  const [ref, setRef] = createSignal<PromptRef | undefined>()
  const args = useArgs()
  const local = useLocal()
  const editor = useEditorContext()
  const dimensions = useTerminalDimensions()
  const tuiConfig = useTuiConfig()
  const promptMaxWidth = createMemo(() => {
    const configured = tuiConfig.prompt?.max_width
    if (configured === "auto") return Math.max(75, Math.floor(dimensions().width * 0.7))
    return configured ?? 75
  })
  const choose = () => dialog.replace(() => (
    <DialogSelect title="¿Qué querés hacer?" options={starters} onSelect={(option) => {
      const task = starters.find((item) => item.value === option.value)
      const current = ref()?.current
      if (!task) return
      if (local.agent.list().some((item) => item.name === task.agent)) local.agent.set(task.agent)
      ref()?.set({ input: task.prompt + (current?.input ? "\n\n" + current.input : ""), parts: current?.parts ?? [] })
      dialog.clear()
      ref()?.focus()
    }} />
  ))
  useBindings(() => ({ commands: [{ name: "cuy.start", namespace: "palette", title: "Elegir una tarea para empezar",
    slashName: "empezar", category: "cuycli", run: choose }] }))
  let sent = false

  onMount(() => {
    editor.clearSelection()
  })

  const bind = (r: PromptRef | undefined) => {
    setRef(r)
    promptRef.set(r)
    if (once || !r) return
    if (route.prompt) {
      r.set(route.prompt)
      once = true
      return
    }
    if (!args.prompt) return
    r.set({ input: args.prompt, parts: [] })
    once = true
  }

  // Wait for sync and model store to be ready before auto-submitting --prompt
  createEffect(() => {
    const r = ref()
    if (sent) return
    if (!r) return
    if (!sync.ready || !local.model.ready) return
    if (!args.prompt) return
    if (r.current.input !== args.prompt) return
    sent = true
    r.submit()
  })

  return (
    <HomeSessionDestinationProvider>
      <box flexGrow={1} alignItems="center" paddingLeft={2} paddingRight={2}>
        <box flexGrow={1} minHeight={0} />
        <box height={1} minHeight={0} flexShrink={1} />
        <box flexShrink={0}>
          <pluginRuntime.Slot name="home_logo" mode="replace">
            <Logo />
          </pluginRuntime.Slot>
        </box>
        <text fg={theme.textMuted}>Tu proyecto, con tus modelos de Databricks.</text>
        <box height={1} minHeight={0} flexShrink={1} />
        <Show when={dimensions().height >= 28}>
          <box width="100%" maxWidth={promptMaxWidth()} flexShrink={0}>
            <CuyOverview />
          </box>
        </Show>
        <box width="100%" maxWidth={promptMaxWidth()} zIndex={1000} paddingTop={1} flexShrink={0}>
          <pluginRuntime.Slot name="home_prompt" mode="replace" ref={bind}>
            <Prompt ref={bind} right={<pluginRuntime.Slot name="home_prompt_right" />} placeholders={placeholder} />
          </pluginRuntime.Slot>
        </box>
        <box width="100%" maxWidth={promptMaxWidth()} paddingTop={1} flexShrink={0}>
          <text fg={theme.primary} wrapMode="word" onMouseDown={choose}>Entender · Revisar · Hacer un cambio → /empezar</text>
          <Show when={dimensions().height >= 24}>
            <text fg={theme.textMuted} wrapMode="word">Escribí tu objetivo. @ agrega archivos · /help muestra la ayuda</text>
            <text fg={theme.textMuted}>Las plantillas preparan el mensaje; vos decidís cuándo enviarlo.</text>
          </Show>
        </box>

        <box flexGrow={1} minHeight={0} />
        <Toast />
      </box>
      <box width="100%" flexShrink={0}>
        <pluginRuntime.Slot name="home_footer" mode="single_winner" />
      </box>
    </HomeSessionDestinationProvider>
  )
}
