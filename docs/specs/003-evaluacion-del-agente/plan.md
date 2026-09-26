# Plan — RFC-003

Spec: [RFC-003](../../rfc/RFC-003-evaluacion-del-agente.md). Aceptado el 2026-09-25.

Python estándar; reutilizar `tareas.correr_tarea`, repositorios temporales nuevos,
pruebas en subprocesos sin shell e informes atómicos fuera del repositorio.
Modo seco valida las pruebas de base; no simula una resolución ni consume tokens.
La guardia del plugin suma además en un ledger exclusivo de la corrida, compartido
entre procesos y casos. Conserva la guardia mensual. Una llamada en vuelo puede exceder
el máximo. Configuración alternativa solo en memoria, sin guardar credenciales.
Los resultados comparan hashes de intocables incluso cuando falla el motor.
Costo incompleto implica total parcial y detener nuevas llamadas.

## Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| P1 | Ejecutar casos secos y tests; no afirmar calidad real sin corrida real. |
| P2 | Modelos del entorno configurado; presupuesto explícito. |
| P3 | Simular motor y ejercitar subprocesos/Git reales en temporales. |
| P4 | Reutilizar hooks existentes y verificar sus firmas. |
| P5 | Hashes, sin heurísticas sobre textos del modelo. |
| P6 | Contabilidad ausente o corrupta bloquea nuevas inferencias. |
| P7 | Barrera local; worktree no es sandbox. |
| P8 | Informe con modelos/versión/hash, nunca config completa ni credenciales. |
| P9 | Biblioteca estándar, sin frameworks ni modelo juez. |
| P10 | Docstrings y decisiones junto al código y a esta spec. |

Violaciones declaradas: ninguna. Los casos son código confiable del mantenedor,
no archivos arbitrarios descargados: sus pruebas se ejecutan localmente.

## Entregables y límites

H1: materialización, clasificación, validación seca. H2: runner real, métricas y presupuesto.
H3: diez casos derivados de regresiones reales y baseline real. H4: comparación.
El baseline real requiere acceso a Databricks; ninguna prueba simulada lo sustituye.
No se publica ni compila un nuevo motor como parte de este cambio Python/plugins.

## Enmienda 1 — diseño del consenso

Autorizada por el dueño tras la revisión cruzada. P1/P3: tests de main separados de
aritmética, errores por fase y recursos; P4: codigo_motivo y límite emitidos por tareas;
P5: validez explícita de inspección; P6: desconocido corta, cero previo se acredita;
P7/P8: no atribuir infraestructura al modelo ni exportar excepciones/secretos;
P2: grupo explícito y configuración efectiva; P9: diez casos y sin nuevas dependencias;
P10: contrato y decisiones en este plan y docstrings. Sin excepciones constitucionales.

Descubrimiento conserva entradas inválidas por caso y su error estructurado. La ejecución
registra cada caso previsto desde el inicio como no ejecutado; marca fase antes de intentar
el motor. Fallos locales previos continúan, fallos globales/desconocidos cortan. Una copia
que falla por disco lleno se clasifica por causa, no por estar dentro del caso.
Costos conocidos se copian antes de inspeccionar integridad. El resumen excluye no ejecutados
y preparación de la tasa de resolución y muestra sus conteos aparte. Por grupo se aplica
la misma función de agregación. El hash incorpora grupo; contenido ilegible invalida el
hash del conjunto completo. Escritura fallida no se reintenta ocultando la excepción.
