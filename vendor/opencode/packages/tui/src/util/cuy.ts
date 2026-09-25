/** Display-only helpers: never expose provider keys or raw response bodies. */
export function workspaceName(value: unknown) {
  if (typeof value !== "string") return "Sin workspace configurado"
  try {
    return new URL(value).hostname || "Sin workspace configurado"
  } catch {
    return "Workspace no disponible"
  }
}

export function monthlyLimit(value: string | undefined) {
  const limit = Number(value ?? 10)
  if (!Number.isFinite(limit) || limit < 0) return "Límite no disponible"
  if (limit === 0) return "Sin límite mensual"
  return `Límite mensual: US$ ${limit.toFixed(2)}`
}

export function recovery(message: string): { title: string; message: string } | undefined {
  if (/type validation failed|expected string.*(?:array|list)/i.test(message))
    return { title: "Respuesta de modelo incompatible", message: "Databricks respondió, pero cuycli no pudo interpretar el formato. Elegí otro modelo con /models. Si persiste, ejecutá python instalar.py para volver a verificar los modelos." }
  if (/\b401\b|unauthorized|invalid access token/i.test(message))
    return { title: "Revisá la credencial de Databricks", message: "La autenticación fue rechazada. Revisá el workspace y la vigencia del token. DATABRICKS_TOKEN del entorno tiene prioridad sobre .env. Para renovarlo: python instalar.py --renovar-token." }
  if (/\b403\b|permission_denied|forbidden/i.test(message))
    return { title: "Acceso denegado", message: "Tu identidad no tiene acceso a esta operación. Revisá con el administrador los permisos sobre el endpoint de Databricks. Cambiar el prompt no resuelve este permiso." }
  if (/\b429\b|rate.?limit/i.test(message))
    return { title: "El servicio alcanzó su límite", message: "Esperá antes de volver a intentar. Si se repite, revisá la capacidad y las cuotas del endpoint de Databricks." }
  if (/timeout|timed out|ECONNREFUSED|ENOTFOUND|fetch failed/i.test(message))
    return { title: "No se pudo completar la conexión", message: "Revisá tu red o VPN y que el workspace esté disponible. Volvé a intentar cuando se restablezca la conexión." }
}

export const starters = [
  { value: "entender", title: "Entender el proyecto", description: "Arquitectura y puntos de entrada · solo lectura", agent: "plan",
    prompt: "Explicame qué hace este proyecto, su arquitectura y por dónde conviene empezar. Revisá los archivos y citá ejemplos concretos. No modifiques nada." },
  { value: "revisar", title: "Revisar un problema", description: "Hallazgos priorizados y próximos pasos · solo lectura", agent: "plan",
    prompt: "Revisá el proyecto buscando errores y riesgos concretos. Priorizá los hallazgos, citá archivo y línea y proponé cómo verificarlos. No modifiques nada." },
  { value: "cambiar", title: "Hacer un cambio", description: "Edición con los permisos configurados · definí tu objetivo", agent: "build",
    prompt: "Quiero hacer este cambio: [describí el objetivo]. Primero revisá el código, explicá qué vas a modificar y después implementá y verificá el resultado." },
]
