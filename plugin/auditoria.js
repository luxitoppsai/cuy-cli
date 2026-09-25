/** Auditoría de intentos y resultados usando identificadores reales del motor. */
import { identidad, resumirLlamada, anotar, limpiarSiHaceFalta, RELEVANTES } from "./lib/auditoria-core.js";

export const Auditoria = async ({ directory }) => {
  const quien = identidad();
  limpiarSiHaceFalta();
  const registrar = (evento, datos = {}) => anotar({
    cuando: new Date().toISOString(), ...quien, directory, evento, ...datos,
  });
  return {
    "tool.execute.before": async (input, output) => {
      if (!RELEVANTES.has(input.tool)) return;
      registrar("herramienta.intento", {
        sesion: input.sessionID, llamada: input.callID, herramienta: input.tool,
        ...resumirLlamada(input.tool, output?.args),
      });
    },
    event: async ({ event }) => {
      const p = event?.properties;
      if (!p) return;
      if (event.type === "permission.asked" || event.type === "permission.replied") {
        registrar(event.type === "permission.asked" ? "permiso.consultado" : "permiso.resuelto", {
          sesion: p.sessionID, permiso: p.permission, solicitud: p.id ?? p.requestID,
          patrones: p.patterns, decision: p.reply,
        });
      }
      if (event.type === "session.created") registrar("sesion.inicio", { sesion: p.info?.id });
      if (event.type === "session.status") registrar("sesion.estado", {
        sesion: p.sessionID, estado: p.status?.type,
      });
      const parte = p.part;
      if (event.type !== "message.part.updated" || parte?.type !== "tool") return;
      if (!["completed", "error"].includes(parte.state?.status)) return;
      if (!RELEVANTES.has(parte.tool)) return;
      registrar("herramienta.resultado", {
        sesion: parte.sessionID, llamada: parte.callID, parte: parte.id,
        herramienta: parte.tool, estado: parte.state.status,
        // No guardar el error o la salida: pueden incluir contenido del proyecto.
        ...resumirLlamada(parte.tool, parte.state.input),
      });
    },
  };
};
