# Costos y contexto en cuycli

## Qué mide el costo

La estimación usa los tokens que devuelve Databricks y las tarifas configuradas por
endpoint. El motor calcula cada paso y el plugin suma `step-finish` con deduplicación;
no vuelve a sumar el acumulado del mensaje. El razonamiento se cobra a la tarifa de
salida una sola vez. La entrada normal, la lectura de caché y la escritura de caché
se separan. Para Chat Completions se conservan los campos superiores de `usage`
que Databricks utiliza para caché y razonamiento.

Fórmula (tarifas USD por millón):

```
(input_sin_cache × input + cache_read × cache_read_rate
 + cache_write × cache_write_rate + output_total × output) / 1_000_000
```

`output_total` ya incluye razonamiento. El total de entrada se interpreta según el
contrato Chat Completions como entrada total, incluidas las categorías de caché.
Se mantiene una prueba que recorre el SDK y el cálculo del motor, no solo la fórmula.

La referencia pública corresponde a endpoints globales de pago por token. No es
una tarifa de contrato verificada. In-geo, prioridad, descuentos, capacidad
provisionada y servicios del gateway pueden cambiar el importe. Por defecto se
asumen USD 0,07 por DBU; `CUY_USD_POR_DBU` permite ajustarlo.

No extrapolamos una tarifa a todas las versiones de una familia. Por ejemplo,
Opus 4/4.1 y Opus 4.5 tienen precios distintos en la referencia publicada. Si una
versión no aparece en la fuente consultada, su precio queda sin referencia, aunque
una instalación antigua tenga un número configurado para ella.

Fuentes consultadas el 2026-09-25:

- https://learn.microsoft.com/en-us/azure/databricks/resources/pricing
- https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/api-reference

## Auditar y calibrar

Desde la carpeta del proyecto, sin hacer llamadas a los modelos:

```powershell
python cuy.py costos
python cuy.py costos --actualizar
```

La actualización reemplaza tarifas con referencia conocida y conserva las demás,
señalándolas como no verificadas. No recalcula registros históricos, que no tienen
el desglose necesario para reconstruirlos de manera fiable. Cerrá y volvé a abrir
cuycli después de actualizar tarifas.

Para usar precios contractuales exactos, creá un JSON con claves iguales a las del
modelo en la configuración y definí `CUY_TARIFAS` con la ruta del archivo. Los cuatro
campos aceptados son `input`, `output`, `cache_read` y `cache_write`, en **USD por
millón de tokens**. `input` y `output` son obligatorios. No incluyas credenciales.
Luego ejecutá `python cuy.py costos --actualizar`. Las tarifas personalizadas tienen
prioridad sobre las públicas.

Si disponés del importe real del **mismo mes y exactamente las mismas solicitudes**:

```powershell
python cuy.py costos --mes 2026-09 --real-usd 12.34
```

Este comando muestra la diferencia absoluta y porcentual. No valida el alcance de
los importes ni aplica factores correctores automáticamente. Sin esa comparación,
no se puede afirmar una precisión del 95% o 99%.

El acumulado local no es la factura del workspace. No cubre necesariamente consultas
de instalación, llamadas auxiliares sin un evento contabilizado, solicitudes fallidas
con consumo, otros equipos, otros clientes ni cargos de infraestructura o gateway.
El tope local se comprueba entre llamadas: no reserva costos futuros ni detiene
peticiones que ya estén en vuelo.

## Cómo funciona el contexto

Lo administra el motor integrado, no una skill adicional:

1. Usa la ventana `limit.context` del modelo configurado y reserva espacio para la
   salida. El porcentaje de la interfaz se refiere a esa ventana configurada,
   que puede ser conservadora y no equivale a consultar el máximo del endpoint.
2. Antes de desbordar, la compactación automática resume el historial antiguo y
   conserva turnos recientes. El resumen también consume tokens y cuesta dinero.
3. Activamos la poda de resultados antiguos de herramientas. El motor protege las
   interacciones recientes, las herramientas de skills y unos 40k tokens de salidas;
   poda cuando puede liberar más de 20k tokens. No borra los archivos del proyecto.
4. Limitamos las salidas de herramientas a 1.000 líneas/24.000 bytes por defecto,
   frente a 2.000/51.200 del motor. Cuando una herramienta usa el truncador, guarda
   la salida completa en disco para recuperar fragmentos concretos si hacen falta.

Se respetan los valores explícitos de `compaction` y `tool_output` del usuario.
No activamos razonamiento extra, ni trasladamos automáticamente los resúmenes a un
modelo más barato: perder contexto puede causar retrabajo y gastar más. Tampoco
agregamos una skill permanente al prompt; una skill no mejora la contabilidad y
consume contexto. Separar conversaciones por objetivo, pedir búsquedas concretas y
revisar fragmentos en vez de repositorios completos sigue siendo útil.
