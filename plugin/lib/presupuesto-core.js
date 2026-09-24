/**
 * Conteo de gasto y decisión del tope de presupuesto.
 *
 * Vive aparte del plugin a propósito: OpenCode trata **cada export** del archivo de
 * plugin como si fuera una fábrica de plugins, así que exportar funciones auxiliares
 * desde ahí rompe la carga —las invoca con el contexto del plugin como argumento—.
 *
 * **Por qué la tarifa se declara y no se lee.** Databricks devuelve tokens, nunca
 * costo. Y no cobra en dólares por token sino en **DBU por millón de tokens**, con un
 * dólar por DBU que depende del contrato de cada empresa. Por eso el cálculo son dos
 * factores separados —tarifa en DBU y dólares por DBU— y ambos se pueden declarar.
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
 * Dólares por DBU. Es el convenio estándar de Model Serving, pero **depende del
 * contrato**: cada empresa negocia el suyo y varía por nube y región.
 */
export const USD_POR_DBU = Number(process.env.CUY_USD_POR_DBU ?? 0.07);

/**
 * Tarifas en **DBU por millón de tokens**, que es como las publica Databricks.
 *
 * Databricks no cobra en dólares por token sino en DBU, y el dólar por DBU depende del
 * contrato: por eso se separan las dos cosas en vez de guardar un precio en dólares.
 *
 * Origen de cada valor, porque no todos tienen la misma confianza:
 * - `haiku` y `sonnet`: tarifas reales de Databricks (haiku confirmada por Luis).
 * - modelos abiertos: tabla publicada de Databricks.
 * - `opus`: **derivada** de la tarifa pública de Anthropic dividido el DBU estándar.
 *   Es la única sin confirmar, y justo la del modelo principal: conviene verificarla.
 *
 * Para los números de tu contrato, escribí `precios.json` con la misma forma.
 */
export const DBU_POR_DEFECTO = {
  opus: { entrada: 214.286, salida: 1071.43 },
  sonnet: { entrada: 42.857, salida: 214.286 },
  haiku: { entrada: 14.286, salida: 71.429 },
  "llama-4-maverick": { entrada: 7.143, salida: 21.429 },
  "llama-3-1-8b": { entrada: 2.143, salida: 6.429 },
  "gpt-oss-20b": { entrada: 1.0, salida: 4.286 },
};

/**
 * Busca la tarifa en DBU de un modelo, por nombre exacto o por familia.
 *
 * @param {string} modelo Identificador del modelo.
 * @param {object} tabla Tarifas declaradas por el usuario, en DBU.
 * @returns {{entrada: number, salida: number}|null} Tarifa, o null si no se conoce.
 */
export function dbuDe(modelo, tabla = {}) {
  if (!modelo) return null;
  if (tabla[modelo]) return tabla[modelo];
  const nombre = String(modelo).toLowerCase();
  const combinadas = { ...DBU_POR_DEFECTO, ...tabla };
  // Primero las claves más específicas: "llama-3-1-8b" debe ganarle a "llama".
  for (const clave of Object.keys(combinadas).sort((a, b) => b.length - a.length)) {
    if (nombre.includes(clave)) return combinadas[clave];
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
 * @param {object} tabla Tarifas declaradas, en DBU por millón de tokens.
 * @param {number} usdPorDbu Dólares por DBU según el contrato.
 * @returns {number} Costo en dólares; 0 si no se conoce la tarifa del modelo.
 */
export function costoDe(uso, modelo, tabla = {}, usdPorDbu = USD_POR_DBU) {
  if (!uso || typeof uso !== "object") return 0;
  const dbu = dbuDe(modelo, tabla);
  if (!dbu) return 0;
  const entrada = Number(uso.input_tokens ?? uso.prompt_tokens ?? 0);
  const salida = Number(uso.output_tokens ?? uso.completion_tokens ?? 0);
  if (!Number.isFinite(entrada) || !Number.isFinite(salida)) return 0;
  const dbusConsumidos = (entrada * dbu.entrada + salida * dbu.salida) / 1_000_000;
  return dbusConsumidos * usdPorDbu;
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
