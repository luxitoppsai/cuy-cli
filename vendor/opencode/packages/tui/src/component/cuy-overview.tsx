import { Show, createMemo } from "solid-js"
import { useLocal } from "../context/local"
import { useSync } from "../context/sync"
import { useTheme } from "../context/theme"
import { monthlyLimit, workspaceName } from "../util/cuy"

export function CuyOverview(props: { compact?: boolean }) {
  const local = useLocal()
  const sync = useSync()
  const { theme } = useTheme()
  const selected = createMemo(() => local.model.current())
  const provider = createMemo(() => sync.data.config.provider?.[selected()?.providerID ?? ""])
  const model = createMemo(() => {
    const item = selected()
    return sync.data.provider.find((p) => p.id === item?.providerID)?.models[item?.modelID ?? ""]?.name
      ?? item?.modelID ?? "Elegí un modelo con /models"
  })
  const mode = createMemo(() => local.agent.current()?.name === "plan"
    ? "Planificar · solo lectura" : local.permission.mode === "auto"
    ? "Editar · aprobación automática activa" : "Editar · permisos configurados")
  return (
    <box backgroundColor={theme.backgroundPanel} paddingLeft={2} paddingRight={2} paddingTop={1} paddingBottom={1} gap={0} width="100%">
      <text fg={theme.primary}><b>Databricks Model Serving</b></text>
      <text fg={theme.textMuted} wrapMode="word">{workspaceName(provider()?.options?.baseURL)}</text>
      <text fg={theme.text} wrapMode="word">Modelo: {model()}</text>
      <text fg={theme.textMuted} wrapMode="word">{mode()}</text>
      <text fg={theme.textMuted} wrapMode="word">{monthlyLimit(process.env.CUY_LIMITE_USD)}</text>
      <Show when={!selected()}>
        <text fg={theme.warning} wrapMode="word">Para empezar: ejecutá python instalar.py y volvé a abrir cuycli.</text>
      </Show>
      <Show when={!props.compact}>
        <text fg={theme.textMuted} wrapMode="word">{sync.ready ? "Configuración cargada · la conexión se comprueba al enviar" : "Cargando configuración…"}</text>
      </Show>
    </box>
  )
}
