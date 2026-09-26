/** Freno local antes de inferencia. No reserva gasto ni cancela otras peticiones en vuelo. */
import { costoDelEvento, evaluar, leerGasto, sumarGasto, LIMITE_USD } from "./lib/presupuesto-core.js";

export const Presupuesto = async ({ client }) => {
  const evaluacion = process.env.CUY_EVALUACION_GASTO;
  const maximo = Number(process.env.CUY_EVALUACION_LIMITE_USD);
  let errorContable;
  let mesAvisado;
  const comprobar = async () => {
  if (evaluacion && (!Number.isFinite(maximo) || maximo <= 0)) {
    throw new Error("Presupuesto de evaluación inválido; indicá un máximo positivo.");
  }

    if (errorContable) throw errorContable;
    if (evaluacion && leerGasto(evaluacion, "2000-01").usd >= maximo) {
      throw new Error("Tope de evaluación alcanzado. Consultá el informe parcial antes de iniciar otra corrida.");
    }
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
        if (event?.type !== "message.part.updated" || event?.properties?.part?.type !== "step-finish") return;
        const parte = event.properties.part;
        // El id del paso hace idempotente un evento repetido/reconectado.
        const id = parte.id ? `${parte.sessionID}:${parte.id}` : undefined;
        sumarGasto(costo, undefined, undefined, id);
        // Una clave fija mantiene el tope de corrida aunque cambie el mes.
        if (evaluacion) sumarGasto(costo, evaluacion, "2000-01", id);
      } catch (error) {
        errorContable = error;
        console.error("CUY: falló la contabilidad; se bloqueará la siguiente inferencia.");
      }
    },
    "chat.params": async (input) => {
      await comprobar();
      const costo = input.model?.cost;
      if ((LIMITE_USD > 0 || evaluacion) && (!costo || !Number.isFinite(costo.input) || !Number.isFinite(costo.output)
          || costo.input <= 0 || costo.output <= 0)) {
        throw new Error(evaluacion
          ? "Modelo sin tarifa configurada. Configurá cost.input/output antes de evaluar; no se permite evaluar sin contabilidad."
          : "Modelo sin tarifa configurada. Configurá cost.input/output o desactivá explícitamente el presupuesto local con CUY_LIMITE_USD=0.");
      }
    },
    "tool.execute.before": comprobar,
  };
};
