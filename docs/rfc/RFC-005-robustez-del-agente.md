---
rfc: RFC-005
titulo: Robustez técnica del agente
estado: aceptado
fecha: 2026-10-08
constitucion: 1.0.1
---

# RFC-005 — Robustez técnica del agente

El usuario aprobó avanzar con las mejoras técnicas en conversación el 2026-10-08.
Confirmó que la ejecución será local, sin contenedores ni runner remoto.
La aceptación autoriza implementar; no significa que las capacidades ya existan.

## Problema y alcance

La conversación libre debe conservar cambios del usuario, recuperar ediciones del
agente y reducir investigación repetida. Los controles deben ser verificables en
código, con evidencia separada para fuente, binario local y release distribuida.

Se entrega por etapas: protección y recuperación de ediciones; permisos comunes;
ejecución local acotada; índice incremental y contexto; límites de operaciones y
auditoría. No se introduce un flujo de inicio ni una dependencia de contenedores.

## Diseño y alternativas

Antes de mutar un archivo, comparar su versión con los bytes usados para preparar
la edición, también después de esperar permisos. Altas y destinos de movimientos
deben seguir ausentes; un parche valida todos sus destinos antes de escribir.
Incluir origen y destino en la autorización de movimientos.

Después se vincularán las versiones a las lecturas de la sesión y se registrarán
preimágenes y resultados para una recuperación que rechace modificaciones externas.
Las copias de recuperación son contenido sensible local, separado de Git y de la
auditoría, con permisos restrictivos. Un diff aprobado no autoriza sobrescribir
cambios que aparezcan durante la espera.

Se prefiere comprobación optimista a bloquear archivos de otros editores. Existe
una ventana entre comprobación y escritura: no es una transacción del sistema de
archivos. Un parche con varios archivos tampoco promete atomicidad ante fallos de
E/S. El undo existente requiere integración antes de afirmar recuperación segura.

Las pruebas del repositorio objetivo ejecutan código local. Se limitarán duración,
salida y entorno, pero no se llamará sandbox a estos límites. No se añaden frameworks
de agentes, watchers residentes ni dependencias de aislamiento sin necesidad medida.

## Requisitos y aceptación

| ID | Requisito |
|---|---|
| RF-001 | Rechazar modificaciones externas ocurridas mientras se aprueba una edición. |
| RF-002 | Evitar sobrescrituras por altas o movimientos y autorizar ambos extremos. |
| RF-003 | Vincular ediciones a lecturas y recuperar solo cambios del agente sin perder cambios del usuario. |
| RF-004 | Unificar permisos y registrar decisiones con versión de política. |
| RF-005 | Acotar ejecución local, cancelación, salida y credenciales heredadas. |
| RF-006 | Mejorar actualización del índice y contexto con versiones de las fuentes. |
| RF-007 | Aplicar límites de operaciones y ampliar auditoría sin contenidos por defecto. |
| CA-001 | Write y edit conservan modificaciones concurrentes y altas concurrentes. |
| CA-002 | Apply_patch valida el conjunto antes de escribir y pide permiso para el destino. |
| CA-003 | Recuperación rechaza archivos modificados posteriormente; conserva bytes originales. |
| CA-004 | Pruebas negativas verifican permisos por herramienta y metadatos de auditoría. |
| CA-005 | Ejecución finaliza procesos, limita salida y no entrega credenciales por defecto. |
| CA-006 | Índice refleja altas, cambios y borrados sin servir versiones obsoletas. |

La primera etapa implementa RF-001, RF-002, CA-001 y CA-002. Los demás requisitos
permanecen pendientes hasta disponer de implementación y pruebas correspondientes.
