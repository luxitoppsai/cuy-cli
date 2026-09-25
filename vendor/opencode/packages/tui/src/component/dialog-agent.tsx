import { createMemo } from "solid-js"
import { useLocal } from "../context/local"
import { DialogSelect } from "../ui/dialog-select"
import { useDialog } from "../ui/dialog"

export function DialogAgent() {
  const local = useLocal()
  const dialog = useDialog()

  const options = createMemo(() =>
    local.agent.list().map((item) => {
      return {
        value: item.name,
        title: item.name === "plan" ? "Planificar · solo lectura" : item.name === "build" ? "Editar · implementar cambios" : item.name,
        description: item.name === "plan" ? "Explorar, entender y proponer sin modificar archivos" : item.name === "build" ? "Modificar y verificar con los permisos configurados" : item.description,
      }
    }),
  )

  return (
    <DialogSelect
      title="Elegí cómo trabajar"
      current={local.agent.current()?.name}
      options={options()}
      onSelect={(option) => {
        local.agent.set(option.value)
        dialog.clear()
      }}
    />
  )
}
