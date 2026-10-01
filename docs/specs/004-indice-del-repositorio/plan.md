# Plan — RFC-004

1. Adaptador `codegraph.py`: descarga fijada, selección de fuentes, copia incremental,
   invalidación de borrados y servidor MCP con herramientas de lectura.
2. Arranque de conversación: determinar directorio, preparar índice y añadir MCP,
   permisos e instrucciones. Los subcomandos informativos y tareas no indexan.
3. Pruebas de fronteras, contrato MCP/motor real y guías de uso.

## Compuerta constitucional (1.0.1)

| Principio | Aplicación |
|---|---|
| P1 | Ejecutar CodeGraph real y registrar búsqueda, cambios y borrados. |
| P2 | Resolver raíz Git y plataforma; rutas relativas portables. |
| P3 | Simular descarga, fallos, protocolo y arranque; contrato real optativo en CI. |
| P4 | Usar esquemas publicados por el binario y contrato MCP del motor. |
| P5 | Exclusiones con pruebas negativas: fuentes normales permanecen disponibles. |
| P6 | Fallos de verificación deshabilitan el índice; no invalidan permisos de Cuy. |
| P7 | Documentar barreras y límites, sin prometer sandbox. |
| P8 | Proceso nativo con entorno mínimo, sin tokens ni logs de contenidos. |
| P9 | Biblioteca estándar; consultas one-shot aprovechan caché sin watcher propio. |
| P10 | RFC, plan, pruebas y evidencia dentro del repositorio. |

La copia de fuentes y el adaptador MCP son complejidad necesaria: el servidor directo
no respeta el conjunto de archivos admitidos ni elimina correctamente todos los
símbolos de archivos borrados al reiniciar. No se modifica el motor ni su release.

Resultados observados y pendientes: [evidencia](evidencia.md).
