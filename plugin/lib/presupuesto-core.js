/**
 * Conteo de gasto y decisión del tope de presupuesto.
 *
 * Vive aparte del plugin a propósito: OpenCode trata **cada export** del archivo de
 * plugin como si fuera una fábrica de plugins, así que exportar funciones auxiliares
 * desde ahí rompe la carga —las invoca con el contexto del plugin como argumento—.
 *
 * **Por qué acá ya no hay tabla de precios.** La había, y calculaba el costo a mano a
 * partir de los tokens. Era trabajo duplicado: OpenCode calcula el costo de cada paso
 * él mismo, siempre que el modelo declare su tarifa en `opencode.json`. Ahora la tarifa
 * se declara una sola vez —`generar_config.py` la traduce de DBU a dólares— y acá solo
 * se suma lo que OpenCode ya calculó.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { conBloqueo, escribirAtomico } from "./archivos.js";

function numero(nombre, defecto) {
  const raw = process.env[nombre] ?? String(defecto);
  const valor = raw.trim() ? Number(raw) : NaN;
  if (!Number.isFinite(valor) || valor < 0) throw new Error(`${nombre} debe ser finito y no negativo`);
  return valor;
}
export const LIMITE_USD = numero("CUY_LIMITE_USD", 10);
export const AVISO = numero("CUY_AVISO_PORCENTAJE", 80);

const CARPETA = path.join(os.homedir(), ".local", "share", "cuy-cli");
export const GASTO_ARCHIVO = process.env.CUY_GASTO ?? path.join(CARPETA, "gasto.json");

/**
 * Saca el costo de un evento, si el evento es el que cierra un paso del modelo.
 *
 * OpenCode emite dos señales con costo y **solo una sirve para sumar**: el mensaje del
 * asistente lleva el costo *acumulado* —sumarlo en cada actualización contaría de más—,
 * mientras que la parte `step-finish` lleva el costo *de ese paso* y se emite una sola
 * vez, con un id nuevo. Se usa la segunda.
 *
 * @param {object} evento Evento recibido en el hook `event`.
 * @returns {number} Costo en dólares del paso, o 0 si el evento no es un cierre de paso.
 */
export function costoDelEvento(evento) {
  if (evento?.type !== "message.part.updated") return 0;
  const parte = evento?.properties?.part;
  if (parte?.type !== "step-finish") return 0;
  const costo = Number(parte.cost);
  return Number.isFinite(costo) && costo > 0 ? costo : 0;
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
function leerDatos(archivo) {
  let datos;
  try {
    datos = JSON.parse(fs.readFileSync(archivo, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return {};
    throw new Error(`No se puede leer el presupuesto ${archivo}; no se asumirá gasto cero.`, { cause: error });
  }
  if (!datos || typeof datos !== "object" || Array.isArray(datos)) throw new Error("Presupuesto inválido");
  if (datos._eventos !== undefined && (!datos._eventos || typeof datos._eventos !== "object"
      || Array.isArray(datos._eventos) || Object.values(datos._eventos).some(ids => !Array.isArray(ids)
        || ids.some(id => typeof id !== "string")))) throw new Error("Índice contable corrupto");
  for (const [mes, usd] of Object.entries(datos)) {
    if (mes === "_eventos") continue;
    if (!/^\d{4}-\d{2}$/.test(mes) || typeof usd !== "number" || !Number.isFinite(usd) || usd < 0) {
      throw new Error("Presupuesto corrupto: se detiene la inferencia hasta repararlo.");
    }
  }
  return datos;
}

export function leerGasto(archivo = GASTO_ARCHIVO, mes = mesActual()) {
  return { mes, usd: leerDatos(archivo)[mes] ?? 0 };
}

/** Actualización entre procesos con exclusión mutua y reemplazo atómico.
 * Un lock huérfano produce un error; nunca se borra un lock de otro proceso a ciegas.
 */
export function sumarGasto(usd, archivo = GASTO_ARCHIVO, mes = mesActual(), eventoID) {
  if (!Number.isFinite(usd) || usd < 0) throw new Error("Costo inválido");
  return conBloqueo(archivo, () => {
    const datos = leerDatos(archivo);
    const ids = datos._eventos?.[mes] ?? [];
    if (eventoID && ids.includes(eventoID)) return datos[mes] ?? 0;
    datos[mes] = (datos[mes] ?? 0) + usd;
    if (!Number.isFinite(datos[mes])) throw new Error("Acumulado fuera de rango");
    if (eventoID) {
      datos._eventos = { ...datos._eventos, [mes]: [...ids, eventoID] };
    }
    escribirAtomico(archivo, JSON.stringify(datos, null, 2));
    return datos[mes];
  });
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
  if (![usd, limite, avisoPorcentaje].every(Number.isFinite) || usd < 0 || limite < 0) {
    throw new Error("Presupuesto o límite inválido");
  }
  if (limite === 0) return { estado: "ok", porcentaje: 0 };
  const porcentaje = Math.round((usd / limite) * 100);
  if (usd >= limite) return { estado: "excedido", porcentaje };
  if (porcentaje >= avisoPorcentaje) return { estado: "aviso", porcentaje };
  return { estado: "ok", porcentaje };
}
