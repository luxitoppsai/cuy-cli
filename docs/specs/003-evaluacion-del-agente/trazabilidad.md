# Trazabilidad — RFC-003

| Criterio | Test | Archivo |
|---|---|---|
| CA-001 | `test_main_diez_casos_json_y_metricas` | `tests/test_evaluar.py` |
| CA-002 | `test_pipeline_real_worktree_pruebas_y_base_ya_verde` | `tests/test_evaluar.py` |
| CA-003 | `test_intocable_borrado_aunque_motor_diga_verificada` | `tests/test_evaluar.py` |
| CA-004 | `test_repo_un_commit_sin_historia` | `tests/test_evaluar.py` |
| CA-005 | `test_configuraciones_comparables_sin_secretos` | `tests/test_evaluar.py` |
| CA-006 | `test_interrupcion_conserva_informe` | `tests/test_evaluar.py` |
| CA-007 | `test_diez_bases_rojas_sin_modelo_y_sin_residuos` | `tests/test_evaluar.py` |
| CA-008 | `test_limite_corrida_y_mensual` | `tests/test_evaluar.py` |
| CA-009 | `test_motor_real_camino_y_contabilidad_parcial_detiene` | `tests/test_evaluar.py` |
| CA-010 | `test_clasificacion_no_infiere_pasos` | `tests/test_evaluar.py` |
| RF-001 | `test_repo_un_commit_sin_historia` | `tests/test_evaluar.py` |
| RF-002 | `test_pipeline_real_worktree_pruebas_y_base_ya_verde` | `tests/test_evaluar.py` |
| RF-003 | `test_intocable_borrado_aunque_motor_diga_verificada` | `tests/test_evaluar.py` |
| RF-004 | `test_clasificacion_no_infiere_pasos` | `tests/test_evaluar.py` |
| RF-005 | `test_configuraciones_comparables_sin_secretos` | `tests/test_evaluar.py` |
| RF-006 | `test_aritmetica_duraciones_y_grupos_parciales` | `tests/test_evaluar.py` |
| RF-007 | `test_config_alternativa_no_muta_politicas_ni_original` | `tests/test_evaluar.py` |
| RF-008 | `test_exige_presupuesto_sin_iniciar_motor` | `tests/test_evaluar.py` |
| RF-009 | `test_limite_corrida_y_mensual` | `tests/test_evaluar.py` |
| RF-010 | `test_fallo_con_costo_no_impide_siguiente_caso` | `tests/test_evaluar.py` |
| RF-011 | `test_diez_bases_rojas_sin_modelo_y_sin_residuos` | `tests/test_evaluar.py` |
| RF-012 | `test_eventos_parciales_y_cero_real` | `tests/test_evaluar.py` |
| RF-013 | `test_clasificacion_no_infiere_pasos` | `tests/test_evaluar.py` |
| RF-014 | `test_aritmetica_duraciones_y_grupos_parciales` | `tests/test_evaluar.py` |
| RF-015 | `test_copia_local_continua_disco_lleno_detiene` | `tests/test_evaluar.py` |
| RF-016 | `test_pipeline_real_worktree_pruebas_y_base_ya_verde` | `tests/test_evaluar.py` |
| CA-011 | `test_preparacion_cero_continua_intento_incierto_corta` | `tests/test_evaluar.py` |
| CA-012 | `test_copia_local_continua_disco_lleno_detiene` | `tests/test_evaluar.py` |
| CA-013 | `test_aritmetica_duraciones_y_grupos_parciales` | `tests/test_evaluar.py` |
| CA-014 | `test_integridad_raiz_invalida_y_borrado_con_error` | `tests/test_evaluar.py` |
| CA-015 | `test_pipeline_real_worktree_pruebas_y_base_ya_verde` | `tests/test_evaluar.py` |
| CA-016 | `máximo inválido no rompe la fábrica y rechaza antes del proveedor` | `tests/evaluacion-presupuesto.test.mjs` |

## Notas

La evidencia usa Git/worktrees/pruebas reales y proveedor simulado: no acredita tasa de
éxito de un modelo de Databricks. H3/H4 (baseline real) siguen pendientes.
CA-004 comprueba un solo commit, sin remotos ni alternates; no descarta memorización del
modelo ni convierte el worktree en sandbox.
La guardia entre inferencias se ejerce además en `tests/evaluacion-presupuesto.test.mjs`:
tope propio, contabilidad ausente y ledger corrupto. No promete reserva de gasto en vuelo.
RF-007 permite selección alternativa; evaluar realmente subagentes queda fuera del flujo
actual de corrección, que no habilita delegación.

## Evidencia complementaria de la enmienda

- CA-001/RF-006: integración de main con diez casos y tiempos reales finitos; agregación
  separada con 1, 2, 9 segundos (total 12, mediana 2), sin confundir promedio con mediana.
- CA-011: manifiesto inválido continúa (`test_manifiesto_invalido_no_impide_caso_siguiente`);
  configuración global detiene (`test_config_global_detiene_antes_de_todos_los_casos`).
- CA-012: persistencia fallida conserva último JSON (`test_fallo_persistencia_conserva_ultimo_informe`).
- CA-015: redacción libre no altera clasificación (`test_motivo_estructurado_no_depende_del_texto`);
  integración deriva un límite efectivo de siete, sin literal duplicado en el evaluador.
- CA-016: fábrica/hooks ejercitados directamente; no se afirma validación visual de TUI.

El conjunto es principalmente un baseline de mecánica de edición y contratos. Sus tres
familias son relacionadas; ni el agregado ni una comparación única demuestran generalización
ni superioridad. Los grupos, objetivos y contenido forman parte del hash cuando se pudieron
inspeccionar todos los casos; con hash null no se afirma identidad del conjunto.
