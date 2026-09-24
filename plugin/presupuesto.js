/**
 * Tope de consumo por sesión.
 *
 * OpenCode cuenta tokens y costo, pero solo los *reporta* después (`opencode stats`):
 * no hay forma de poner un límite. Un agente en loop puede gastar mucho antes de que
 * alguien mire. Este plugin pone el tope que falta.
 *
 * Se cuenta en **tokens, no en dólares**, porque el precio de un endpoint de Databricks
 * depende de la modalidad contratada y no viaja en la respuesta; los tokens sí son
 * exactos y observables.
 *
 * Configuración por variables de entorno:
 *   CUY_LIMITE_TOKENS     tope por sesión (default 300000; 0 lo desactiva)
 *   CUY_AVISO_PORCENTAJE  a qué porcentaje avisar (default 80)
 *
 * **Este archivo exporta una sola cosa, a propósito.** OpenCode trata cada export como
 * una fábrica de plugins y la invoca con el contexto: exportar una función auxiliar
 * desde acá rompe la carga del plugin y, en cascada, deja la configuración nula. La
 * lógica testeable vive en `lib/presupuesto-core.js`.
 */

import { contarTokens, buscarUso, evaluar, LIMITE } from "./lib/presupuesto-core.js";

export const Presupuesto = async ({ client }) => {
  let usados = 0;
  let yaAviso = false;

  const acumular = (evento) => {
    const uso = buscarUso(evento);
    if (uso) usados += contarTokens(uso);
  };

  return {
    "message.updated": async (input) => acumular(input),
    "message.part.updated": async (input) => acumular(input),

    "tool.execute.before": async () => {
      const { estado, porcentaje } = evaluar(usados);

      if (estado === "excedido") {
        // Lanzar acá aborta la operación: es el único punto donde se puede frenar
        // al agente antes de que siga consumiendo.
        throw new Error(
          `Tope de presupuesto alcanzado: ${usados.toLocaleString()} tokens de ` +
            `${LIMITE.toLocaleString()} en esta sesión. Abrí una sesión nueva, o subí ` +
            `CUY_LIMITE_TOKENS si de verdad hace falta.`
        );
      }

      if (estado === "aviso" && !yaAviso) {
        yaAviso = true;
        try {
          await client.tui?.showToast?.({
            message: `Presupuesto al ${porcentaje}% (${usados.toLocaleString()} tokens)`,
            variant: "warning",
          });
        } catch {
          // La notificación es un extra: si la API cambió, no se interrumpe la sesión.
        }
      }
    },
  };
};
