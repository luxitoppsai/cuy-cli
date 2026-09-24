/**
 * Registro de auditoría: qué tocó el agente y cuánto consumió, por persona.
 *
 * OpenCode ya guarda sesiones y mensajes en su base local, pero sin identidad de quién
 * los originó y en un formato pensado para la herramienta, no para revisarlo. Esto
 * escribe un registro paralelo, en JSONL, pensado para leerlo después.
 *
 * **Qué es y qué no es.** Es atribución, no prueba: el archivo lo escribe el mismo
 * usuario cuya actividad registra, así que puede editarlo. Sirve para responder "qué
 * hizo el agente en mi máquina" y para repartir consumo, no para sostener una
 * acusación.
 *
 * Configuración por variables de entorno:
 *   CUY_AUDITORIA        ruta del archivo (default ~/.local/share/cuy-cli/auditoria.jsonl)
 *   CUY_AUDITORIA_OFF    si vale "1", no registra nada
 *   CUY_RETENCION_DIAS   días a conservar (default 90; 0 conserva todo)
 *
 * **Este archivo exporta una sola cosa, a propósito** — ver la nota equivalente en
 * `presupuesto.js`. La lógica testeable vive en `lib/auditoria-core.js`.
 */

import {
  identidad,
  resumirLlamada,
  anotar,
  limpiarSiHaceFalta,
  RELEVANTES,
} from "./lib/auditoria-core.js";

export const Auditoria = async ({ directory }) => {
  const quien = identidad();
  const sesion = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  let acciones = 0;

  limpiarSiHaceFalta();
  anotar({ cuando: new Date().toISOString(), sesion, ...quien, evento: "sesion.inicio", directory });

  return {
    "tool.execute.before": async (input) => {
      const herramienta = input?.tool ?? input?.name ?? "desconocida";
      if (!RELEVANTES.has(herramienta)) return;
      acciones++;
      anotar({
        cuando: new Date().toISOString(),
        sesion,
        ...quien,
        evento: "herramienta",
        herramienta,
        ...resumirLlamada(herramienta, input?.args ?? input?.input),
      });
    },

    // Deja constancia de lo que la política bloqueó o preguntó: es la mitad
    // interesante de una auditoría, y la que no queda en ningún otro lado.
    "permission.asked": async (input) => {
      anotar({
        cuando: new Date().toISOString(),
        sesion,
        ...quien,
        evento: "permiso.consultado",
        permiso: input?.permission ?? input?.type,
        patron: String(input?.pattern ?? "").slice(0, 200),
      });
    },

    "session.idle": async () => {
      anotar({ cuando: new Date().toISOString(), sesion, ...quien, evento: "sesion.fin", acciones });
    },
  };
};
