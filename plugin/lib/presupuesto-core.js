/**
 * Conteo de gasto y decisión del tope de presupuesto.
 *
 * Vive aparte del plugin a propósito: OpenCode trata **cada export** del archivo de
 * plugin como si fuera una fábrica de plugins, así que exportar funciones auxiliares
 * desde ahí rompe la carga —las invoca con el contexto del plugin como argumento—.
 *
 * **Por qué el precio se declara y no se lee.** Databricks devuelve tokens, nunca
 * costo: el precio depende de la modalidad contratada y del acuerdo de cada empresa.
 * Los valores por defecto son las tarifas públicas de Anthropic y sirven como
 * estimación; el número real se pone en `precios.json` (ver `PRECIOS_ARCHIVO`).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const LIMITE_USD = Number(process.env.CUY_LIMITE_USD ?? 10);
export const AVISO = Number(process.env.CUY_AVISO_PORCENTAJE ?? 80);

const CARPETA = path.join(os.homedir(), ".local", "share", "cuy-cli");
export const GASTO_ARCHIVO = process.env.CUY_GASTO ?? path.join(CARPETA, "gasto.json");
export const PRECIOS_ARCHIVO = process.env.CUY_PRECIOS ?? path.join(CARPETA, "precios.json");

/**
 * Precio por millón de tokens, como estimación.
 *
 * Son las tarifas públicas de Anthropic. **No son las de tu contrato**: para números
 * reales, escribí `precios.json` con la forma
 * ``{"databricks-claude-opus-4-1": {"entrada": 15, "salida": 75}}``.
 */
export const PRECIOS_POR_DEFECTO = {
  opus: { entrada: 15, salida: 75 },
  sonnet: { entrada: 3, salida: 15 },
  haiku: { entrada: 0.8, salida: 4 },
};

/**
 * Busca el precio de un modelo, por nombre exacto o por familia.
 *
 * @param {string} modelo Identificador del modelo.
 * @param {object} tabla Precios declarados por el usuario.
 * @returns {{entrada: number, salida: number}|null} Precio, o null si no se conoce.
 */
export function precioDe(modelo, tabla = {}) {
  if (!modelo) return null;
  if (tabla[modelo]) return tabla[modelo];
  const nombre = String(modelo).toLowerCase();
  for (const [familia, precio] of Object.entries({ ...PRECIOS_POR_DEFECTO, ...tabla })) {
    if (nombre.includes(familia)) return precio;
  }
  return null;
}

/**
 * Calcula el costo en dólares de un uso concreto.
 *
 * Los nombres de los contadores difieren entre proveedores (`input_tokens` en
 * Anthropic, `prompt_tokens` en OpenAI) y Databricks devuelve uno u otro según el
 * endpoint: se aceptan ambos.
 *
 * @param {object} uso Objeto de uso de la respuesta.
 * @param {string} modelo Modelo que la produjo.
 * @param {object} tabla Precios declarados.
 * @returns {number} Costo en dólares; 0 si no se puede calcular.
 */
export function costoDe(uso, modelo, tabla = {}) {
  if (!uso || typeof uso !== "object") return 0;
  const precio = precioDe(modelo, tabla);
  if (!precio) return 0;
  const entrada = Number(uso.input_tokens ?? uso.prompt_tokens ?? 0);
  const salida = Number(uso.output_tokens ?? uso.completion_tokens ?? 0);
  if (!Number.isFinite(entrada) || !Number.isFinite(salida)) return 0;
  return (entrada * precio.entrada + salida * precio.salida) / 1_000_000;
}

/**
 * Busca el objeto de uso dentro de un evento, sin asumir su ubicación exacta.
 *
 * La forma de los eventos cambia entre versiones, así que se recorre el objeto en vez
 * de fijar una ruta. Perder la cuenta es preferible a romper la sesión del usuario.
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

/** Mes actual como ``AAAA-MM``, que es la clave con la que se acumula el gasto. */
export function mesActual(fecha = new Date()) {
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}`;
}

/**
 * Lee el gasto acumulado del mes en curso.
 *
 * Se guarda por mes en vez de un total corrido para que el tope se libere solo al
 * cambiar de mes, sin que nadie tenga que acordarse de resetearlo.
 *
 * @returns {{mes: string, usd: number}}
 */
export function leerGasto(archivo = GASTO_ARCHIVO, mes = mesActual()) {
  try {
    const datos = JSON.parse(fs.readFileSync(archivo, "utf8"));
    return { mes, usd: Number(datos[mes]) || 0 };
  } catch {
    return { mes, usd: 0 };
  }
}

/**
 * Suma gasto al mes en curso y devuelve el nuevo acumulado.
 *
 * Conserva los meses anteriores: sirven para revisar consumo histórico.
 *
 * @returns {number} Acumulado del mes tras sumar.
 */
export function sumarGasto(usd, archivo = GASTO_ARCHIVO, mes = mesActual()) {
  let datos = {};
  try {
    datos = JSON.parse(fs.readFileSync(archivo, "utf8"));
  } catch {
    datos = {};
  }
  datos[mes] = (Number(datos[mes]) || 0) + usd;
  try {
    fs.mkdirSync(path.dirname(archivo), { recursive: true });
    fs.writeFileSync(archivo, JSON.stringify(datos, null, 2));
  } catch {
    // Contabilizar es importante, pero no al punto de romper la sesión.
  }
  return datos[mes];
}

/** Precios declarados por el usuario, si existen. */
export function leerPrecios(archivo = PRECIOS_ARCHIVO) {
  try {
    return JSON.parse(fs.readFileSync(archivo, "utf8"));
  } catch {
    return {};
  }
}

/**
 * Decide qué hacer con el gasto acumulado.
 *
 * @param {number} usd Gasto del mes.
 * @param {number} limite Tope en dólares; 0 o menos desactiva el control.
 * @param {number} avisoPorcentaje Umbral de aviso.
 * @returns {{estado: "ok"|"aviso"|"excedido", porcentaje: number}}
 */
export function evaluar(usd, limite = LIMITE_USD, avisoPorcentaje = AVISO) {
  if (!limite || limite <= 0) return { estado: "ok", porcentaje: 0 };
  const porcentaje = Math.round((usd / limite) * 100);
  if (usd >= limite) return { estado: "excedido", porcentaje };
  if (porcentaje >= avisoPorcentaje) return { estado: "aviso", porcentaje };
  return { estado: "ok", porcentaje };
}
