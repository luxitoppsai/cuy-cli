# Plan — RFC-006

1. Política de presupuesto fija y plugins incorporados obligatorios en el motor.
2. Separar recursos de aplicación y datos locales; entrada compilada con instalación,
   configuración e inicio MCP, reutilizando configuración existente.
3. Preparador de paquetes por plataforma, runtime incluido y manifiesto de hashes;
   instalador nativo Windows x64 con Inno Setup y validación silenciosa en CI.
4. Regresiones, compilación real, contratos y documentación de uso/mantenimiento.

## Compuerta constitucional (1.0.1)

| Principio | Aplicación |
|---|---|
| P1 | Probar el paquete real y motor compilado; no acreditar plataformas no ejecutadas. |
| P2 | Compilar para SO/arquitectura del intérprete, descubrir rutas y validar motor. |
| P3 | Cubrir instalación, recursos, configuración y ruta MCP con fixtures; CI nativa. |
| P4 | Usar interfaces Plugin y PyInstaller verificadas en documentación y código. |
| P5 | Ignorar solo opciones de presupuesto; conservar configuración útil y datos. |
| P6 | Plugins obligatorios no se omiten por errores; rechazar importes inválidos. |
| P7 | Empaquetado y política fija son barreras locales con límites explícitos. |
| P8 | Solo recursos enumerados; excluir .env/config del paquete y registros. |
| P9 | Reutilizar Python y motor; una dependencia de compilación, sin framework nuevo. |
| P10 | RFC, mantenimiento y evidencia en repo; ajuste fuera del README. |

PyInstaller se usa solo al preparar paquetes. Evita reescribir las utilidades en
TypeScript y no añade dependencias al equipo destinatario. No se cifra el código
ni se promete impedir ingeniería inversa.
Inno Setup se usa solo en el runner Windows: resuelve la instalación gráfica sin
introducir un servicio privilegiado ni pedir que el usuario ejecute scripts.
