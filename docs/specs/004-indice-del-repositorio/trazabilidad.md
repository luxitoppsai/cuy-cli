# Trazabilidad — RFC-004

| Identificador | Test | Archivo |
|---|---|---|
| RF-001 | `test_configuracion_y_arranque_de_conversacion` | `tests/test_codegraph.py` |
| RF-002 | `test_borrados_invalidan_cache_y_copia` | `tests/test_codegraph.py` |
| RF-003 | `test_indice_separa_repos_y_traduce_rutas` | `tests/test_codegraph.py` |
| RF-004 | `test_gitignore_preserva_crlf_y_no_duplica` | `tests/test_codegraph.py` |
| RF-005 | `test_entorno_nativo_no_recibe_credenciales` | `tests/test_codegraph.py` |
| RF-006 | `test_fallo_del_indice_conserva_entorno` | `tests/test_codegraph.py` |
| CA-001 | `test_copia_reutiliza_y_actualiza_archivos` | `tests/test_codegraph.py` |
| CA-002 | `test_indice_real_actualiza_altas_cambios_y_borrados` | `tests/test_codegraph.py` |
| CA-003 | `test_fuentes_respeta_git_y_excluye_secretos` | `tests/test_codegraph.py` |
| CA-004 | `test_mcp_solo_expone_y_ejecuta_lectura` | `tests/test_codegraph.py` |
| CA-005 | `test_descarga_rechaza_checksum_sin_reemplazar` | `tests/test_codegraph.py` |
| CA-006 | `test_motor_consulta_codegraph_con_permisos_de_lectura` | `tests/test_motor.py` |

Las pruebas de contrato requieren `CUY_TEST_CODEGRAPH` y, para la última,
`CUY_TEST_BINARIO`. Su omisión no acredita el contrato real. Las pruebas de enlaces,
plataformas y bloqueo complementan la selección de archivos y la descarga.
