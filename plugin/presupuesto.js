/**
 * Tope de gasto mensual.
 *
 * OpenCode cuenta tokens y costo, pero solo los *reporta* después (`opencode stats`):
 * no hay forma de poner un límite. Un agente en loop puede gastar mucho antes de que
 * alguien mire. Este plugin pone el tope que falta.
 *
 * El gasto se acumula **por mes** y el tope se libera solo al cambiar de mes, para que
 * nadie tenga que acordarse de resetearlo.
 *
 * Configuración por variables de entorno:
 *   CUY_LIMITE_USD        tope mensual en dólares (default 10; 0 lo desactiva)
 *   CUY_AVISO_PORCENTAJE  a qué porcentaje avisar (default 80)
 *   CUY_PRECIOS           ruta del archivo de precios por modelo
 *
 * **Este archivo exporta una sola cosa, a propósito.** OpenCode trata cada export como
 * una fábrica de plugins y la invoca con el contexto: exportar una función auxiliar
 * desde acá rompe la carga del plugin y, en cascada, deja la configuración nula. La
 * lógica testeable vive en `lib/presupuesto-core.js`.
 */

import {
  buscarUso,
  costoDe,
  evaluar,
  leerGasto,
  leerPrecios,
  sumarGasto,
  LIMITE_USD,
} from "./lib/presupuesto-core.js";

const dolares = (n) => `$${n.toFixed(2)}`;

export const Presupuesto = async ({ client }) => {
  const precios = leerPrecios();
  let acumulado = leerGasto().usd;
  let yaAviso = false;
  let modelo = "";

  const acumular = (evento) => {
    // El modelo viaja en el evento junto al uso; se recuerda el último visto porque
    // el precio depende de él y no siempre llegan en el mismo mensaje.
    const posible = evento?.modelID ?? evento?.model ?? evento?.info?.modelID;
    if (typeof posible === "string" && posible) modelo = posible;

    const uso = buscarUso(evento);
    if (!uso) return;
    const costo = costoDe(uso, modelo, precios);
    if (costo > 0) acumulado = sumarGasto(costo);
  };

  return {
    "message.updated": async (input) => acumular(input),
    "message.part.updated": async (input) => acumular(input),

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
