---
tipo: plan
spec: RFC-NNN
proyecto: cuy-cli
fecha: AAAA-MM-DD
constitucion: 1.0.0
---

# Plan — RFC-NNN, {{título}}

> Spec: [`docs/rfc/RFC-NNN-slug.md`](../../rfc/RFC-NNN-slug.md)
>
> **No se escribe hasta que el RFC esté `aceptado`.**

## Resumen

Dos o tres frases: qué se construye y con qué enfoque. Si no entra en tres frases, el
alcance del RFC es demasiado grande.

## Contexto técnico

| | |
|---|---|
| Lenguaje | |
| Dependencias nuevas | *ninguna, o por qué hace falta* |
| Punto de integración | |
| Almacenamiento | |
| Pruebas | |
| Escala | *volumen y frecuencia esperados* |

Lo que no se sepa se escribe `PENDIENTE DE AVERIGUAR` y se resuelve antes de implementar,
no durante.

## Compuerta constitucional

Se recorren **los diez principios**. Ninguno se omite; "no aplica" es una respuesta válida
y hay que escribirla.

| Principio | Cumplimiento |
|---|---|
| **P1** Verificar, no deducir | |
| **P2** Descubrir, no asumir | |
| **P3** Camino sin cubrir | |
| **P4** API que ignora en silencio | |
| **P5** Precisión sobre cobertura | |
| **P6** Fallar cerrado | |
| **P7** Barrera vs control | |
| **P8** El secreto no toca el disco | |
| **P9** KISS / YAGNI | |
| **P10** El porqué donde vive el código | |

**Violaciones declaradas:** *ninguna*, o una fila por cada una con: qué principio, por qué
hace falta, y qué alternativa más simple se descartó. Una violación declarada es una
decisión; una silenciosa es deuda.

## Diseño

Cómo se resuelve. Módulos, flujo de datos, dónde se engancha. Las decisiones no obvias se
justifican acá y, si son estructurales, además como ADR en el vault.

## Estructura

Los archivos que se crean o se tocan.

## Riesgos

Los del RFC §7 más los que aparezcan al diseñar.
