---
rfc: RFC-006
titulo: Distribución compilada y presupuesto fijado por el mantenedor
estado: aceptado
fecha: 2026-10-08
constitucion: 1.0.1
---

# RFC-006 — Distribución compilada

El usuario aprobó distribuir un compilado instalable sin clonar el repositorio,
con presupuesto mensual fijo y ajuste reservado al mantenedor fuera del README.
Aceptó una barrera local contra cambios durante el uso normal, no protección frente
a administradores ni sustitución del ejecutable. Se conserva USD 10 por defecto.

## Alcance y diseño

Empaquetar el lanzador Python con su intérprete, recursos y motor Cuy mediante
PyInstaller, compilado en cada sistema de destino. El paquete no contiene checkout,
fuentes Python/JavaScript ni herramientas de desarrollo. El ejecutable ofrece
`instalar` para copiar la aplicación al espacio del usuario, y `configurar` para
preparar Databricks o renovar la credencial. No requiere Python, Node ni Bun instalados;
Git sigue siendo necesario para las operaciones del proyecto que utilizan Git.

En Windows x64, Inno Setup añade un instalador `.exe` para copiar el paquete y
crear accesos de configuración/diagnóstico, sin elevación. La CI lo instala en
modo silencioso en una carpeta temporal y ejecuta la versión del programa instalado.
En macOS/Linux se entrega el paquete completo con instalación desde su ejecutable.

Los datos de conexión se almacenan aparte de la aplicación. CodeGraph se inicia
mediante el mismo ejecutable empaquetado, sin buscar un intérprete Python externo.
Presupuesto, auditoría y secretos se incorporan al motor como plugins obligatorios
en la distribución, sin depender de archivos JavaScript editables ni de flags que
deshabilitan plugins opcionales. El importe se fija al preparar el artefacto; no
hay interruptor de presupuesto ni ajuste por variables del entorno en ejecución.

El ajuste del mantenedor consiste en producir una distribución nueva. No se añaden
contraseñas ocultas ni claves privadas dentro del ejecutable. El procedimiento se
documenta para mantenimiento, fuera del README de uso. Tener acceso al repositorio
permite conocerlo: el acceso a las fuentes debe restringirse por el equipo.

Alternativas: entregar solo OpenCode deja el lanzador y plugins en fuentes; una
constante Python sin empaquetar resulta editable; un servicio privilegiado supone
administración del equipo fuera del alcance aprobado. Un paquete congelado evita
entregar fuentes directamente, pero su código puede analizarse o recuperarse.

## Límites

La contabilidad continúa local y basada en tarifas estimadas; se puede superar el
tope con llamadas simultáneas o en curso. Borrar o alterar el estado, cambiar el reloj,
modificar precios o usar el token en otro cliente quedan fuera de la garantía.
No se promete código imposible de extraer ni un límite de facturación duro.
Firmas de distribución y validación nativa por plataforma se registran por separado.

## Requisitos

| ID | Requisito |
|---|---|
| RF-001 | Distribuir ejecutable, runtime, motor y recursos sin checkout ni fuentes editables. |
| RF-002 | Instalar y configurar sin Python, Node o Bun en el equipo usuario. |
| RF-003 | Ignorar ajustes de presupuesto por entorno y cargar siempre los plugins incorporados. |
| RF-004 | Permitir cambiar el importe durante preparación de una distribución, fuera del README. |
| RF-005 | Ejecutar CodeGraph y comandos de diagnóstico con el paquete compilado. |
| RF-006 | Conservar datos existentes durante instalación y distinguir plataformas verificadas. |

## Aceptación

| ID | Criterio |
|---|---|
| CA-001 | El paquete real no contiene .py/.js de Cuy, credenciales ni fuentes vendor. |
| CA-002 | Instalación, ayuda, versión y diagnóstico ejecutan sin intérpretes externos. |
| CA-003 | Presupuesto agotado impide inferencia aunque se intente desactivarlo por entorno/configuración. |
| CA-004 | Un importe de compilación diferente se refleja en política y bloqueo del motor real. |
| CA-005 | MCP CodeGraph se inicia desde el ejecutable congelado y responde a una consulta. |
| CA-006 | Reinstalar conserva configuración, credenciales y contabilidad. |
