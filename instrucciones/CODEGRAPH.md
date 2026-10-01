# Consultar el mapa del repositorio

Las herramientas `cuy_codegraph_*` consultan un índice local de fuentes. Úsalas cuando
necesites localizar símbolos, dependencias, llamadas o el impacto de un cambio.
Para búsquedas textuales sencillas, usa las herramientas habituales.

Busca símbolos antes de consultar sus identificadores y relaciones. Los resultados
muestran rutas del proyecto original. Lee los archivos originales antes de editar:
el grafo es análisis estático y puede omitir llamadas dinámicas o lenguajes no cubiertos.
Si una herramienta falla, continúa leyendo y buscando archivos, e informa la limitación
cuando afecte una conclusión. No afirmes cobertura completa por un resultado vacío.

El índice excluye archivos ocultos, ignorados por Git, enlaces, dependencias y ciertas
carpetas convencionales. La lectura normal sigue disponible para esos archivos cuando
sea pertinente y los permisos lo permitan. Las consultas revisan los cambios locales;
no requieren commits ni un comando de inicio.

Esta integración no contiene memoria persistente del agente, historial Git ni otros
repositorios. Las descripciones nativas pueden mencionar esas capacidades generales
de CodeGraph; aquí solo están disponibles las relaciones de las fuentes del proyecto.
