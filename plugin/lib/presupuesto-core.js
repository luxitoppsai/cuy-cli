/**
 * Lógica de conteo y decisión del tope de presupuesto.
 *
 * Vive aparte del plugin a propósito: OpenCode trata **cada export** del archivo de
 * plugin como si fuera una fábrica de plugins, así que exportar funciones auxiliares
 * desde ahí rompe la carga —las invoca con el contexto del plugin como argumento—.
 */

export const LIMITE = Number(process.env.CUY_LIMITE_TOKENS ?? 300000);
const AVISO = Number(process.env.CUY_AVISO_PORCENTAJE ?? 80);

/**
 * Suma los tokens de un objeto de uso, sea cual sea la forma en que venga.
 *
 * Los proveedores no coinciden en los nombres —`input_tokens` en Anthropic,
 * `prompt_tokens` en OpenAI— y Databricks devuelve una u otra según el endpoint.
 * Se aceptan las dos y se ignora lo que no sea un número.
 *
 * @param {object} uso Objeto de uso de una respuesta.
 * @returns {number} Tokens totales, o 0 si no se pudo leer.
 */
export function contarTokens(uso) {
  if (!uso || typeof uso !== "object") return 0;
  const entrada = uso.input_tokens ?? uso.prompt_tokens ?? uso.input ?? 0;
  const salida = uso.output_tokens ?? uso.completion_tokens ?? uso.output ?? 0;
  const total = uso.total_tokens ?? uso.total;
  if (typeof total === "number" && Number.isFinite(total)) return total;
  const suma = Number(entrada) + Number(salida);
  return Number.isFinite(suma) ? suma : 0;
}

/**
 * Busca el objeto de uso dentro de un evento, sin asumir su ubicación exacta.
 *
 * La forma de los eventos cambia entre versiones de OpenCode, así que se recorre el
 * objeto en vez de fijar una ruta. Es deliberadamente tolerante: perder la cuenta es
 * preferible a romper la sesión del usuario por un cambio de esquema.
 *
 * @param {object} nodo Evento recibido en el hook.
 * @param {number} profundidad Control interno de recursión.
 * @returns {object|null} El objeto de uso, o null.
 */
export function buscarUso(nodo, profundidad = 0) {
  if (!nodo || typeof nodo !== "object" || profundidad > 6) return null;
  if (nodo.usage && typeof nodo.usage === "object") return nodo.usage;
  if ("input_tokens" in nodo || "prompt_tokens" in nodo) return nodo;
  for (const valor of Object.values(nodo)) {
    const encontrado = buscarUso(valor, profundidad + 1);
    if (encontrado) return encontrado;
  }
  return null;
}

/**
 * Decide qué hacer con el consumo acumulado.
 *
 * @param {number} usados Tokens consumidos en la sesión.
 * @param {number} limite Tope configurado; 0 o menos desactiva el control.
 * @param {number} avisoPorcentaje Umbral de aviso.
 * @returns {{estado: "ok"|"aviso"|"excedido", porcentaje: number}}
 */
export function evaluar(usados, limite = LIMITE, avisoPorcentaje = AVISO) {
  if (!limite || limite <= 0) return { estado: "ok", porcentaje: 0 };
  const porcentaje = Math.round((usados / limite) * 100);
  if (usados >= limite) return { estado: "excedido", porcentaje };
  if (porcentaje >= avisoPorcentaje) return { estado: "aviso", porcentaje };
  return { estado: "ok", porcentaje };
}
