/**
 * Lógica de identidad, resumen y retención del registro de auditoría.
 *
 * Separada del plugin por el mismo motivo que `presupuesto-core.js`: OpenCode toma
 * cada export del archivo de plugin como una fábrica de plugins.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DESTINO =
  process.env.CUY_AUDITORIA ||
  path.join(os.homedir(), ".local", "share", "cuy-cli", "auditoria.jsonl");
const APAGADO = process.env.CUY_AUDITORIA_OFF === "1";
const RETENCION_DIAS = Number(process.env.CUY_RETENCION_DIAS ?? 90);

/** Herramientas cuyo uso importa registrar: las que cambian algo o salen del proyecto. */
export const RELEVANTES = new Set(["bash", "edit", "write", "patch", "webfetch", "websearch"]);

/**
 * Identifica de quién es la actividad.
 *
 * Se usa el usuario del sistema operativo: no hay autenticación propia, y pretender
 * que la hay sería peor que admitir el límite.
 *
 * @returns {{usuario: string, equipo: string}}
 */
export function identidad() {
  let usuario = "desconocido";
  try {
    usuario = os.userInfo().username;
  } catch {
    usuario = process.env.USER || process.env.USERNAME || "desconocido";
  }
  return { usuario, equipo: os.hostname() };
}

/**
 * Extrae de una llamada a herramienta lo que vale auditar, sin guardar el contenido.
 *
 * Se registra *qué* se hizo, no el texto de los archivos: un registro de auditoría con
 * el código adentro es una filtración esperando ocurrir, y además crece sin control.
 *
 * @param {string} herramienta Nombre de la herramienta.
 * @param {object} argumentos Argumentos con los que se invocó.
 * @returns {object} Datos seguros para registrar.
 */
export function resumirLlamada(herramienta, argumentos = {}) {
  const a = argumentos || {};
  switch (herramienta) {
    case "bash":
      return { comando: String(a.command ?? a.cmd ?? "").slice(0, 500) };
    case "edit":
    case "write":
    case "patch":
      return { archivo: String(a.filePath ?? a.path ?? a.file ?? "") };
    case "webfetch":
      return { url: String(a.url ?? "").slice(0, 300) };
    case "websearch":
      return { consulta: String(a.query ?? "").slice(0, 200) };
    default:
      return {};
  }
}

/**
 * Descarta las líneas anteriores al período de retención.
 *
 * Un registro que crece para siempre termina borrándose entero el día que molesta.
 * Definir la retención desde el principio lo evita.
 *
 * @param {string[]} lineas Contenido actual, una entrada JSON por línea.
 * @param {number} dias Días a conservar; 0 o menos conserva todo.
 * @param {number} ahora Marca temporal de referencia, en milisegundos.
 * @returns {string[]} Las líneas que se conservan.
 */
export function aplicarRetencion(lineas, dias = RETENCION_DIAS, ahora = Date.now()) {
  if (!dias || dias <= 0) return lineas;
  const corte = ahora - dias * 24 * 60 * 60 * 1000;
  return lineas.filter((linea) => {
    try {
      return new Date(JSON.parse(linea).cuando).getTime() >= corte;
    } catch {
      return false; // una línea ilegible no aporta nada a la auditoría
    }
  });
}

export function anotar(entrada) {
  if (APAGADO) return;
  try {
    fs.mkdirSync(path.dirname(DESTINO), { recursive: true });
    fs.appendFileSync(DESTINO, JSON.stringify(entrada) + "\n");
  } catch {
    // Registrar es importante, pero no al punto de romperle la sesión a alguien.
  }
}

export function limpiarSiHaceFalta() {
  if (APAGADO || !RETENCION_DIAS || RETENCION_DIAS <= 0) return;
  try {
    if (!fs.existsSync(DESTINO)) return;
    const lineas = fs.readFileSync(DESTINO, "utf8").split("\n").filter(Boolean);
    const conservadas = aplicarRetencion(lineas);
    if (conservadas.length !== lineas.length) {
      fs.writeFileSync(DESTINO, conservadas.join("\n") + (conservadas.length ? "\n" : ""));
    }
  } catch {
    // idem
  }
}
