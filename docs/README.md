# Documentación de cuy-cli

Para instalar y empezar, consulta el [README principal](../README.md).

## Guías vigentes

| Necesito… | Documento |
|---|---|
| Configurar credenciales, gasto o carpetas de datos | [Configuración](CONFIGURACION.md) |
| Revisar, aplicar y limpiar una corrección | [Correcciones](CORRECCIONES.md) |
| Conocer permisos, auditoría y límites del motor | [Referencia técnica](REFERENCIA.md) |
| Entender las tarifas y el contexto | [Costos y contexto](COSTOS-Y-CONTEXTO.md) |
| Entender el índice automático de símbolos y dependencias | [Índice del repositorio](INDICE-DEL-REPOSITORIO.md) |
| Preparar desarrollo, probar o distribuir una versión | [Desarrollo y distribución](DESARROLLO.md) |
| Medir correcciones con casos de prueba | [Evaluación del agente](../evaluacion/README.md) |
| Ver resultados simulados | [Demo HTML](demo.html) · [captura](demo.png) |

Las [buenas prácticas compartidas](../instrucciones/AGENTS.md) se aplican a la conversación
libre; el [AGENTS.md del repositorio](../AGENTS.md) añade las reglas para desarrollar Cuy.

## Especificaciones e historial

- [Proceso de especificaciones](SDD.md) y [constitución](CONSTITUCION.md): reglas para contribuir.
- [RFC inicial](../RFC.md): registro histórico de la base del proyecto.
- [RFC-002](rfc/RFC-002-redaccion-de-secretos.md): redacción de secretos. Implementado, con límites aclarados en el propio RFC.
- [RFC-003](rfc/RFC-003-evaluacion-del-agente.md): evaluador. Implementación local y pruebas; baseline con Databricks pendiente. [Estado de tareas](specs/003-evaluacion-del-agente/tareas.md).
- [RFC-004](rfc/RFC-004-indice-del-repositorio.md): índice local de CodeGraph al abrir una conversación. [Plan y evidencia](specs/004-indice-del-repositorio/plan.md).
- [Evolución](EVOLUCION.md): propuestas y próximos pasos; no constituye una lista de funciones disponibles.
- [Plantilla de plan](plantillas/plan.md), [tareas](plantillas/tareas.md) y [trazabilidad](plantillas/trazabilidad.md).

Los RFC conservan el contexto de las decisiones. Las aclaraciones posteriores se identifican
con fecha; una propuesta o una prueba simulada no acredita comportamiento en producción.

## Convenciones de rutas

Los enlaces son relativos al repositorio y funcionan al copiarlo o cambiar su remoto.
`URL_DEL_REPOSITORIO` es un marcador que se sustituye por la URL de clonación del equipo.
`cuy-cli` es el nombre local usado en los ejemplos; no obliga a usar ese nombre en el servidor.
Las rutas como `/ruta/al/repo` o `C:\ruta\al\repo` son ejemplos sustituibles.
`~` representa la carpeta personal del usuario, también al describir el almacenamiento en Windows.
Los comandos parten de la raíz del repositorio salvo indicación expresa.
