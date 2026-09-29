# Buenas prácticas de trabajo

Estas reglas orientan la conversación libre. No requieren comandos de inicio ni un flujo
especial. Respeta las instrucciones explícitas del usuario y las convenciones específicas
del proyecto; ante un conflicto relevante, señala cuál es antes de continuar.

## Entender y acordar

- Lee el código y las instrucciones relevantes antes de modificarlo. No supongas capacidades de una API ni detalles del entorno: compruébalos.
- Para una función nueva de alcance significativo o un cambio de arquitectura, define problema, alcance, alternativas y criterios de aceptación en un RFC del repositorio antes de implementar. Reutiliza un acuerdo ya aprobado; no pidas autorizarlo otra vez.
- Para arreglos pequeños, documentación y tareas cuyo alcance ya está claro, actúa y verifica. Pregunta cuando falte una decisión que afecte el resultado, no por detalles rutinarios.
- Mantén el objetivo y las restricciones al continuar una conversación. Si cambia el alcance, hazlo explícito y actualiza la documentación correspondiente.

## Diseñar y programar

- KISS: elige la solución más sencilla que resuelva el problema completo.
- YAGNI: evita abstracciones, dependencias, opciones y capas para necesidades hipotéticas. Prefiere las herramientas existentes y la biblioteca estándar cuando sean suficientes.
- Usa clases cuando agrupen estado y comportamiento o definan límites útiles. Para lógica simple, prefiere funciones. Aplica SOLID con criterio, sin crear jerarquías innecesarias.
- Valida entradas externas en los límites: usuario, archivos, APIs. No ocultes errores con capturas generales ni agregues validación defensiva duplicada a todo el código interno.
- Usa nombres claros, responsabilidades concretas y las convenciones del repositorio. En Python, documenta interfaces públicas con docstrings Sphinx/reST cuando corresponda; explica decisiones no obvias.
- Antes de añadir frameworks de agentes u orquestación, identifica la necesidad concreta. Prefiere integración directa o el SDK existente; justifica grafos, ciclos o capas adicionales en una decisión documentada.
- Conserva los cambios previos del usuario y evita modificaciones ajenas al objetivo.

## Verificar y entregar

- Ejecuta las comprobaciones pertinentes con los permisos disponibles. Si no puedes ejecutar algo, informa el motivo; no presentes una propuesta de prueba como una prueba realizada.
- Agrega regresiones cuando el riesgo lo justifique. No cambies expectativas ni elimines pruebas solo para obtener un resultado verde.
- Revisa el diff antes de terminar: corrección, alcance, secretos y complejidad innecesaria. Busca qué se puede simplificar sin perder comportamiento.
- Distingue evidencia observada, inferencias y pendientes. Resume qué cambió, por qué, cómo se verificó y las limitaciones relevantes.
- Registra decisiones y causas de bugs no obvios junto al código o en documentos del repositorio. Mantén las instrucciones de uso afectadas actualizadas.

## Datos y herramientas

- No publiques credenciales ni las incluyas en commits, logs, fixtures o ejemplos. Usa los mecanismos de configuración del proyecto.
- Respeta los permisos de herramientas. No desactives controles para hacer pasar una tarea ni atribuyas garantías de seguridad a instrucciones Markdown.
- No presupongas rutas personales, proveedores de Git, plugins o servicios que no estén disponibles. Los documentos necesarios para mantener el proyecto deben ser accesibles desde el repositorio.
