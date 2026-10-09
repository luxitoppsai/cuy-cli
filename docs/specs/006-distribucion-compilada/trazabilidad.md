# Trazabilidad — RFC-006

| Identificador | Test | Archivo |
|---|---|---|
| RF-001 | `test_paquete_no_entrega_fuentes_ni_credenciales` | `tests/test_distribucion.py` |
| RF-002 | `test_instalacion_ayuda_y_version_sin_interpretes` | `tests/test_distribucion.py` |
| RF-003 | `test_presupuesto_incorporado_no_se_desactiva_con_env_o_config` | `tests/test_motor.py` |
| RF-004 | `test_politica_del_motor_coincide_con_importe_de_compilacion` | `tests/test_motor.py` |
| RF-005 | `test_mcp_desde_paquete_sin_python_externo` | `tests/test_distribucion.py` |
| RF-006 | `test_instalacion_y_reinstalacion_conservan_datos` | `tests/test_distribucion.py` |
| CA-001 | `test_paquete_no_entrega_fuentes_ni_credenciales` | `tests/test_distribucion.py` |
| CA-002 | `test_diagnostico_y_gasto_del_paquete_sin_modelo` | `tests/test_distribucion.py` |
| CA-003 | `test_presupuesto_incorporado_no_se_desactiva_con_env_o_config` | `tests/test_motor.py` |
| CA-004 | `test_politica_del_motor_coincide_con_importe_de_compilacion` | `tests/test_motor.py` |
| CA-005 | `test_mcp_desde_paquete_sin_python_externo` | `tests/test_distribucion.py` |
| CA-006 | `test_instalacion_y_reinstalacion_conservan_datos` | `tests/test_distribucion.py` |

Las pruebas del paquete requieren `CUY_TEST_PAQUETE`; MCP requiere además
`CUY_TEST_CODEGRAPH`. Las del motor requieren `CUY_TEST_BINARIO`; el presupuesto
alternativo probado se indica con `CUY_TEST_PRESUPUESTO_USD`, solo en el harness.
La cobertura declarada no acredita Windows/Linux hasta ejecutar sus artefactos.
