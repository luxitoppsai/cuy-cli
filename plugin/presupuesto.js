/** Freno local antes de inferencia. No reserva gasto ni cancela otras peticiones en vuelo. */
import { costoDelEvento, evaluar, leerGasto, sumarGasto, LIMITE_USD } from "./lib/presupuesto-core.js";

export const Presupuesto = async ({ client }) => {
  let errorContable;
  let mesAvisado;
  const comprobar = async () => {
    if (errorContable) throw errorContable;
    const { mes, usd } = leerGasto();
    const { estado, porcentaje } = evaluar(usd);
    if (estado === "excedido") {
      throw new Error(`Tope mensual alcanzado: $${usd.toFixed(2)} de $${LIMITE_USD.toFixed(2)}. Inferencia detenida.`);
    }
    if (estado === "aviso" && mesAvisado !== mes) {
      mesAvisado = mes;
      try {
        await client.tui?.showToast?.({ body: {
          message: `Presupuesto al ${porcentaje}% ($${usd.toFixed(2)})`, variant: "warning",
        } });
      } catch { /* La notificación no modifica el control. */ }
    }
  };
  return {
    event: async ({ event }) => {
      try {
        const costo = costoDelEvento(event);
        if (!costo) return;
        const parte = event.properties.part;
        // El id del paso hace idempotente un evento repetido/reconectado.
        sumarGasto(costo, undefined, undefined, parte.id ? `${parte.sessionID}:${parte.id}` : undefined);
      } catch (error) {
        errorContable = error;
        console.error("CUY: falló la contabilidad; se bloqueará la siguiente inferencia.");
      }
    },
    "chat.params": async (input) => {
      await comprobar();
      const costo = input.model?.cost;
      if (LIMITE_USD > 0 && (!costo || !Number.isFinite(costo.input) || !Number.isFinite(costo.output)
          || costo.input <= 0 || costo.output <= 0)) {
        throw new Error("Modelo sin tarifa configurada. Configurá cost.input/output o desactivá explícitamente el presupuesto local con CUY_LIMITE_USD=0.");
      }
    },
    "tool.execute.before": comprobar,
  };
};
