/**
 * Redacción de secretos antes de que salgan hacia el modelo (RFC-002).
 *
 * Los permisos controlan **qué herramientas** corre el agente; esto controla **qué
 * contenido sale**. Sin él, un `cat .env` o un `grep -r password .` manda credenciales
 * al endpoint de inferencia, donde quedan en logs con otra audiencia y otra retención
 * que el repositorio de donde salieron.
 *
 * Dos mecanismos, porque fallan distinto:
 *
 *   - `tool.execute.before` **rechaza** las rutas cuyo contenido es el secreto (`.env`,
 *     `*.pem`, `~/.aws/credentials`). Redactarlas no serviría de nada.
 *   - `tool.execute.after` **redacta** patrones reconocibles en la salida de cualquier
 *     herramienta, incluida `bash`, que es por donde entra lo que se escapa.
 *
 * **No hay variable de entorno para apagarlo** (D6 del RFC). El tope de gasto sí la
 * tiene, porque es presupuesto personal; una barrera con interruptor se apaga el día que
 * molesta, que es exactamente el día que hace falta.
 *
 * **Este archivo exporta una sola cosa, a propósito** — ver la nota en `presupuesto.js`.
 */

import {
  redactar,
  rutaDe,
  rutaProhibida,
  rutaProhibidaEnComando,
  mensajeDeRechazo,
} from "./lib/secretos-core.js";
import { identidad, anotar } from "./lib/auditoria-core.js";

/** Campos de la salida que pueden traer contenido de archivos. */
const CAMPOS = ["output", "title"];

export const Secretos = async () => {
  const quien = identidad();

  return {
    "tool.execute.before": async (input, output) => {
      const ruta = rutaDe(output?.args);
      if (ruta && rutaProhibida(ruta)) {
        // Lanzar acá aborta la llamada: el contenido nunca se lee.
        throw new Error(mensajeDeRechazo(ruta));
      }
      const comando = output?.args?.command;
      const enComando = rutaProhibidaEnComando(comando);
      if (enComando) throw new Error(mensajeDeRechazo(enComando));
    },

    "tool.execute.after": async (input, output) => {
      if (!output) return;
      const hallazgos = [];
      for (const campo of CAMPOS) {
        if (typeof output[campo] !== "string") continue;
        const resultado = redactar(output[campo]);
        if (!resultado.hallazgos.length) continue;
        // Mutar acá es lo que el modelo termina viendo: OpenCode devuelve este mismo
        // objeto después de disparar el hook.
        output[campo] = resultado.texto;
        hallazgos.push(...resultado.hallazgos);
      }
      if (!hallazgos.length) return;

      // Se registra qué se encontró y cuánto, **nunca el valor**.
      anotar({
        cuando: new Date().toISOString(),
        ...quien,
        evento: "secreto.redactado",
        herramienta: input?.tool,
        ruta: rutaDe(input?.args) ?? undefined,
        hallazgos,
      });
    },
  };
};
