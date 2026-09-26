---
tipo: proceso
proyecto: cuy-cli
fecha: 2026-09-25
---

# Cómo se trabaja acá — desarrollo dirigido por especificación

Mezcla deliberada: la estructura de [Spec Kit](https://github.com/github/spec-kit)
—constitución con compuerta, identificadores estables, plan y tareas— sobre la convención de
RFC que ya rige en todos los proyectos. **El RFC es la spec**; no hay un `spec.md` aparte que
diga lo mismo en otro archivo.

Lo que no trae ninguno de los dos y sí está acá es la **trazabilidad**: cada criterio de
aceptación nombra el test que lo prueba, y un test verifica que esa correspondencia exista.

## Los cuatro documentos

| Documento | Responde | Dónde vive |
|---|---|---|
| **Constitución** | Qué invariantes respeta todo lo que construimos | `docs/CONSTITUCION.md` |
| **RFC (spec)** | Qué problema, qué entra, qué **no**, cómo se sabe que está hecho | `docs/rfc/RFC-NNN-slug.md` |
| **Plan** | Cómo se resuelve, y si respeta la constitución | `docs/specs/NNN-slug/plan.md` |
| **Tareas** | En qué orden, en trozos verificables por separado | `docs/specs/NNN-slug/tareas.md` |
| **Trazabilidad** | Qué test prueba cada criterio | `docs/specs/NNN-slug/trazabilidad.md` |

El RFC sigue donde manda el `CLAUDE.md` global. Lo derivado cuelga de `docs/specs/`.

## El flujo

```
1. RFC          escribir la spec            → estado: borrador
2. Aceptar      revisarla con el dueño      → estado: aceptado
3. Plan         diseño + compuerta          ← acá se cae lo que viola la constitución
4. Tareas       descomponer                 → T001, T002…
5. Implementar  tarea por tarea
6. Trazar       completar trazabilidad.md   → test_trazabilidad.py en verde
```

**No se programa con el RFC en borrador.** Y no se cierra una spec sin trazabilidad: un
criterio sin test es una promesa sin comprobar.

## Identificadores

Estables desde que se escriben. Nunca se renumeran: si un requisito muere, se marca
`(retirado)` y su número no se reutiliza.

| Prefijo | Qué es | Vive en |
|---|---|---|
| `RF-001` | Requisito funcional — qué **debe** hacer el sistema | RFC §Requisitos |
| `CA-001` | Criterio de aceptación — cómo se comprueba | RFC §Criterios |
| `T001` | Tarea de implementación | `tareas.md` |
| `P1` | Principio de la constitución | `CONSTITUCION.md` |

Las tareas se marcan `T003 [P]` cuando pueden correr en paralelo con las de su bloque
—archivos distintos, sin dependencia entre ellas—.

## La compuerta constitucional

Es la parte de Spec Kit que más rinde y la razón de mezclar. Antes de escribir código, el
plan recorre los diez principios y dice, para cada uno, cómo lo cumple o por qué no aplica.

Lo que no se puede hacer es **omitirlo**. Si una decisión viola un principio, se declara en
la sección de complejidad del plan con: qué principio, por qué hace falta, y qué alternativa
más simple se descartó. Una violación declarada es una decisión; una violación silenciosa es
deuda.

## La trazabilidad

`trazabilidad.md` es una tabla de tres columnas: criterio, test que lo prueba, y estado.
`tests/test_trazabilidad.py` comprueba tres cosas y falla si alguna no se cumple:

1. Todo `CA-NNN` del RFC aparece en la tabla.
2. Todo test nombrado en la tabla existe de verdad en el repo.
3. Ningún `CA-NNN` de la tabla dejó de existir en el RFC.

No comprueba que el test *pruebe* lo que dice —eso no lo puede saber un script— pero sí que
nadie escriba un criterio y se olvide de cubrirlo, que es el modo de fallo real.

## Alcance de la adopción

- **RFC-001** queda como registro histórico. Cubre todo lo construido hasta septiembre 2026
  y reconstruirle plan y tareas no movería la aguja.
- **RFC-002** tiene el flujo completo, como ejemplo trabajado: sus cinco criterios ya se
  habían verificado a mano, así que la trazabilidad documenta algo real.
- **RFC-003 en adelante** nacen con el flujo completo.
