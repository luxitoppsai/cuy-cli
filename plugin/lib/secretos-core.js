/**
 * Detección de secretos en lo que sale hacia el modelo (RFC-002).
 *
 * Vive aparte del plugin a propósito: OpenCode trata **cada export** del archivo de
 * plugin como una fábrica de plugins, así que exportar funciones auxiliares desde ahí
 * rompe la carga.
 *
 * **Qué es y qué no es.** Es una barrera contra el accidente, no un control: el plugin
 * corre en la máquina del usuario y se puede editar. Sirve para que `cat .env` no
 * termine en los logs de inferencia, no para detener a alguien decidido. El control duro
 * vive en el Gateway de Databricks.
 *
 * **Precisión sobre cobertura, a propósito.** Un falso positivo es peor que un falso
 * negativo acá: el modelo ve `[REDACTADO]` donde había código legítimo y razona sobre
 * una mentira. La lista crece con casos reales, no con hipótesis.
 */

import path from "node:path";

/**
 * Archivos cuyo contenido **es** el secreto: se rechazan enteros en vez de redactarse.
 *
 * Redactarlos no le serviría al modelo —quedaría un archivo de `[REDACTADO]`— y daría la
 * ilusión de que lo leyó. El error le dice la verdad: está fuera de alcance.
 */
/**
 * Plantillas que se llaman como un secreto pero existen justamente para versionarse:
 * `.env.example` es la lista de variables **sin** valores, y leerla es lo correcto.
 */
const PLANTILLAS = /\.(example|sample|template|dist|tpl)(\.\w+)?$/i;

export const RUTAS_PROHIBIDAS = [
  /(^|[/\\])\.env(\.|$)/i,
  /(^|[/\\])\.env$/i,
  /\.pem$/i,
  /\.p12$/i,
  /\.pfx$/i,
  /(^|[/\\])id_(rsa|dsa|ecdsa|ed25519)(\.|$)/i,
  /(^|[/\\])\.credentials\.json$/i,
  /(^|[/\\])credentials\.json$/i,
  /(^|[/\\])terraform\.tfvars$/i,
  /(^|[/\\])\.npmrc$/i,
  /(^|[/\\])\.pypirc$/i,
  /(^|[/\\])\.databrickscfg$/i,
  /(^|[/\\])\.aws[/\\]credentials$/i,
  /(^|[/\\])\.ssh[/\\]/i,
  /(^|[/\\])service[-_]account.*\.json$/i,
];

/**
 * Valores que parecen secreto pero no lo son. Sin esto, la propia configuración de este
 * proyecto —`"apiKey": "{env:DATABRICKS_TOKEN}"`— se redactaría a sí misma.
 */
const MARCADORES = [
  /^\{env:/i,
  /^\$\{?[A-Z_]+\}?$/,
  /^<.*>$/,
  /^\*+$/,
  /^x+$/i,
  /^(changeme|placeholder|your[-_ ]?\w+|dummy|example|redactado|redacted|none|null|true|false)$/i,
  /^(tu|mi)[-_]token$/i,
];

const esMarcador = (valor) => MARCADORES.some((re) => re.test(valor.trim()));

/**
 * Patrones con forma inconfundible. Cada uno redacta solo lo que capturó.
 *
 * El orden importa poco porque no se solapan, pero las claves privadas van primero para
 * que su bloque entero desaparezca antes de que otro patrón lo toque por dentro.
 */
export const PATRONES = [
  {
    tipo: "clave-privada",
    re: /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
  },
  { tipo: "databricks-pat", re: /\bdapi[0-9a-f]{32}\b/g },
  { tipo: "aws-access-key", re: /\bAKIA[0-9A-Z]{16}\b/g },
  { tipo: "github", re: /\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})\b/g },
  { tipo: "slack", re: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/g },
  { tipo: "anthropic", re: /\bsk-ant-[A-Za-z0-9_-]{20,}\b/g },
  { tipo: "openai", re: /\bsk-(?!ant-)[A-Za-z0-9_-]{20,}\b/g },
  { tipo: "google-api-key", re: /\bAIza[A-Za-z0-9_-]{35}\b/g },
];

/**
 * Asignación explícita de algo que se llama secreto.
 *
 * **Solo con el valor entre comillas**, y esa restricción es la que hace usable el
 * patrón: en código, `token = response.token` o `self.api_key = clave` son líneas
 * normales que no deben tocarse, y no llevan comillas. Lo que sí las lleva es un secreto
 * pegado a mano, que es el caso que interesa.
 */
const ASIGNACION =
  /\b(password|passwd|secret|client[_-]?secret|api[_-]?key|access[_-]?key|auth[_-]?token|private[_-]?key)\b(\s*[:=]\s*)(["'`])([^"'`\n]{6,})\3/gi;

/**
 * Reemplaza los secretos de un texto, conservando la forma del resto.
 *
 * @param {string} texto Contenido a revisar.
 * @returns {{texto: string, hallazgos: Array<{tipo: string, cantidad: number}>}}
 *   El texto ya redactado y qué se encontró. Nunca incluye el valor encontrado.
 */
export function redactar(texto) {
  if (typeof texto !== "string" || !texto) return { texto, hallazgos: [] };

  const cuenta = new Map();
  const anotar = (tipo) => cuenta.set(tipo, (cuenta.get(tipo) ?? 0) + 1);

  let salida = texto;
  for (const { tipo, re } of PATRONES) {
    salida = salida.replace(re, () => {
      anotar(tipo);
      return `[REDACTADO:${tipo}]`;
    });
  }

  salida = salida.replace(ASIGNACION, (entero, clave, separador, comilla, valor) => {
    // Ya redactado por un patrón anterior, o un placeholder de la propia config.
    if (valor.startsWith("[REDACTADO:") || esMarcador(valor)) return entero;
    anotar("asignacion");
    return `${clave}${separador}${comilla}[REDACTADO:asignacion]${comilla}`;
  });

  const hallazgos = [...cuenta].map(([tipo, cantidad]) => ({ tipo, cantidad }));
  return { texto: salida, hallazgos };
}

/**
 * Dice si una ruta está fuera de alcance.
 *
 * @param {string} ruta Ruta a revisar, absoluta o relativa.
 * @returns {boolean}
 */
export function rutaProhibida(ruta) {
  if (typeof ruta !== "string" || !ruta) return false;
  const normal = ruta.replace(/\\/g, "/");
  if (PLANTILLAS.test(normal)) return false;
  return RUTAS_PROHIBIDAS.some((re) => re.test(normal));
}

/**
 * Busca rutas prohibidas dentro de un comando de shell.
 *
 * Es deliberadamente simple: parte el comando en palabras y revisa cada una. No intenta
 * entender la sintaxis del shell —un `cat $(echo .env)` se le escapa— porque para eso
 * está la redacción de la salida, que sí lo agarra. Acá alcanza con cubrir lo que
 * cualquiera escribiría sin pensar.
 *
 * @param {string} comando Comando a revisar.
 * @returns {string|null} La primera ruta prohibida encontrada, o ``null``.
 */
export function rutaProhibidaEnComando(comando) {
  if (typeof comando !== "string" || !comando) return null;
  for (const palabra of comando.split(/[\s;|&<>()'"]+/)) {
    if (palabra && rutaProhibida(palabra)) return palabra;
  }
  return null;
}

/** Herramientas cuyo argumento de ruta hay que revisar antes de ejecutarlas. */
export const ARGUMENTOS_DE_RUTA = ["filePath", "path", "file", "filepath"];

/**
 * Saca la ruta que una llamada a herramienta va a tocar, sin asumir el nombre del campo.
 *
 * @param {object} args Argumentos de la llamada.
 * @returns {string|null}
 */
export function rutaDe(args) {
  if (!args || typeof args !== "object") return null;
  for (const clave of ARGUMENTOS_DE_RUTA) {
    if (typeof args[clave] === "string" && args[clave]) return args[clave];
  }
  return null;
}

/** Texto del error con el que se rechaza una lectura. Explica, no solo prohíbe. */
export function mensajeDeRechazo(ruta) {
  return (
    `Lectura bloqueada: ${path.basename(ruta)} suele contener credenciales, ` +
    `y su contenido saldría hacia el modelo. Si necesitás saber qué variables define, ` +
    `pedí las claves sin los valores.`
  );
}
