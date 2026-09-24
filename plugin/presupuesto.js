/**
 * Tope de gasto mensual.
 *
 * OpenCode cuenta tokens y costo, pero solo los *reporta*: no hay forma de poner un
 * límite. Un agente en loop puede gastar mucho antes de que alguien mire. Este plugin
 * pone el tope que falta.
 *
 * El gasto se acumula **por mes** y el tope se libera solo al cambiar de mes, para que
 * nadie tenga que acordarse de resetearlo.
 *
 * Configuración por variables de entorno:
 *   CUY_LIMITE_USD        tope mensual en dólares (default 10; 0 lo desactiva)
 *   CUY_AVISO_PORCENTAJE  a qué porcentaje avisar (default 80)
 *
 * **Los eventos llegan por el hook `event`, no por hooks con su nombre.** La primera
 * versión declaraba `"message.updated"` y `"message.part.updated"` como hooks de primer
 * nivel; OpenCode solo invoca los nombres que están en su interfaz `Hooks`, así que esos
 * dos no se llamaban nunca y el presupuesto jamás contó un centavo —sin error ni aviso,
 * solo un `gasto.json` que no aparecía—.
 *
 * **Este archivo exporta una sola cosa, a propósito.** OpenCode trata cada export como
 * una fábrica de plugins y la invoca con el contexto: exportar una función auxiliar
 * desde acá rompe la carga del plugin y, en cascada, deja la configuración nula. La
 * lógica testeable vive en `lib/presupuesto-core.js`.
 */

import {
  costoDelEvento,
  evaluar,
  leerGasto,
  sumarGasto,
  LIMITE_USD,
} from "./lib/presupuesto-core.js";

const dolares = (n) => `$${n.toFixed(2)}`;

export const Presupuesto = async ({ client }) => {
  let acumulado = leerGasto().usd;
  let yaAviso = false;

  return {
    event: async ({ event }) => {
      const costo = costoDelEvento(event);
      if (costo > 0) acumulado = sumarGasto(costo);
    },

    "tool.execute.before": async () => {
      const { estado, porcentaje } = evaluar(acumulado);

      if (estado === "excedido") {
        // Lanzar acá aborta la operación: es el único punto donde se puede frenar
        // al agente antes de que siga consumiendo.
        throw new Error(
          `Tope mensual alcanzado: ${dolares(acumulado)} de ${dolares(LIMITE_USD)} este mes. ` +
            `Se libera solo el mes que viene. Para subirlo, CUY_LIMITE_USD.`
        );
      }

      if (estado === "aviso" && !yaAviso) {
        yaAviso = true;
        try {
          await client.tui?.showToast?.({
            message: `Presupuesto al ${porcentaje}% (${dolares(acumulado)} de ${dolares(LIMITE_USD)})`,
            variant: "warning",
          });
        } catch {
          // La notificación es un extra: si la API cambió, no se interrumpe la sesión.
        }
      }
    },
  };
};
