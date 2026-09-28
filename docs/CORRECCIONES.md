# Revisar y aplicar una corrección

`cuy tarea corregir` prepara un worktree separado. No modifica automáticamente el repositorio
original ni crea commits. Esta guía parte de una tarea terminada; usa las rutas que figuran
en su `resultado.json`:

- `proyecto`: repositorio original.
- `trabajo`: worktree donde se ejecutó la corrección.
- `base`: commit desde el que partió.
- `diff`: patch exportado, cuando llegó a generarse.

Los marcadores `RUTA_PROYECTO`, `RUTA_WORKTREE` y `RUTA_PATCH` se sustituyen por esas rutas.
Los comandos Git siguientes sirven en macOS, Linux y PowerShell, incluyendo rutas con espacios.

## 1. Inspeccionar

Lee el estado, los archivos afectados y los resultados de pruebas del informe. Después:

```sh
git -C "RUTA_WORKTREE" status --short
git -C "RUTA_WORKTREE" diff --stat
git -C "RUTA_WORKTREE" diff
```

`git diff` no muestra el contenido de los archivos nuevos sin seguimiento: revísalos también
y abre `cambios.patch`, que sí los incluye. Si editas el worktree después de la tarea,
el patch exportado no se actualiza automáticamente.

«Verificada» indica que pasaron las pruebas elegidas y las comprobaciones del flujo.
No demuestra ausencia de errores. Una tarea fallida o interrumpida puede conservar el
worktree sin haber generado un patch; no la trates como una corrección terminada.

## 2. Comprobar el destino y aplicar

En el repositorio original, comprueba la rama, el estado y el commit actual:

```sh
git -C "RUTA_PROYECTO" status --short --branch
git -C "RUTA_PROYECTO" rev-parse HEAD
```

Trabaja sobre un árbol limpio. Compara el commit con `base`: si cambió desde la tarea,
revisa la compatibilidad antes de aplicar. Puedes crear una rama para revisar la corrección:

```sh
git -C "RUTA_PROYECTO" switch -c revision-cuy
```

Elige otro nombre si esa rama ya existe. Primero verifica que el patch se puede aplicar:

```sh
git -C "RUTA_PROYECTO" apply --check "RUTA_PATCH"
```

Solo si termina correctamente, aplícalo:

```sh
git -C "RUTA_PROYECTO" apply "RUTA_PATCH"
git -C "RUTA_PROYECTO" status --short
git -C "RUTA_PROYECTO" diff
```

Si hay conflictos, conserva el worktree y resuélvelos conscientemente o vuelve a ejecutar
la tarea sobre la nueva base. No fuerces la aplicación sin revisar la causa.
Ejecuta las pruebas relevantes desde el proyecto original; después crea el commit y la
solicitud de revisión según el proceso de tu equipo.

## 3. Limpiar el worktree

Cuando hayas aplicado y comprobado la corrección, o decidido descartarla, revisa por última
vez que no queda trabajo que quieras conservar. Puedes listar los worktrees con:

```sh
git -C "RUTA_PROYECTO" worktree list
```

El worktree de una corrección normalmente contiene cambios sin commit. El siguiente comando
los elimina: úsalo únicamente después de conservar lo necesario o decidir descartarlos.

```sh
git -C "RUTA_PROYECTO" worktree remove --force "RUTA_WORKTREE"
```

El informe, `base.json` y el patch permanecen en la carpeta de la tarea. Puedes archivarlos
o eliminar esa carpeta cuando ya no los necesites, conforme a la retención del equipo.
No elimines la carpeta completa antes de retirar el worktree con Git.
