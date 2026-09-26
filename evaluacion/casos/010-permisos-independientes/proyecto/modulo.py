PERMISOS_BASE = {
    # Leer, buscar y navegar el proyecto no necesita aprobación.
    "*": "allow",
    # Salir del proyecto y traer cosas de internet sí: son la vía de escape típica.
    "external_directory": "ask",
    "webfetch": "ask",
    "websearch": "ask",
    # Llamadas idénticas repetidas: el síntoma de un agente en loop, que además gasta.
    "doom_loop": "ask",
    "bash": {
        # Por defecto se pregunta: la lista de abajo habilita lo cotidiano.
        "*": "ask",
        # Lectura e inspección: sin riesgo.
        "ls *": "allow", "cat *": "allow", "head *": "allow", "tail *": "allow",
        "grep *": "allow", "rg *": "allow", "find *": "allow", "wc *": "allow",
        "pwd": "allow", "which *": "allow", "echo *": "allow",
        # Git de solo lectura.
        "git status*": "allow", "git diff*": "allow", "git log*": "allow",
        "git show*": "allow", "git branch": "allow",
        # Correr pruebas y linters es el ciclo normal de trabajo.
        "pytest*": "allow", "python3 -m pytest*": "allow", "python3 -m unittest*": "allow",
        "npm test*": "allow", "npm run *": "allow", "make *": "allow",
        # Irreversible o fuera del proyecto: se bloquea, no se pregunta.
        "rm -rf *": "deny", "rm -r *": "deny",
        "sudo *": "deny",
        "git push --force*": "deny", "git push -f*": "deny",
        "git reset --hard*": "deny", "git clean *": "deny",
        "* > /dev/sd*": "deny", "mkfs*": "deny", "dd *": "deny",
        # Ejecutar lo que se descarga de internet sin leerlo.
        "curl * | sh": "deny", "curl * | bash": "deny",
        "wget * | sh": "deny", "wget * | bash": "deny",
    },
}
def construir_permisos() -> dict:
    """Devuelve la política de permisos por defecto.

    Es un punto de partida razonable, no una respuesta definitiva: cada equipo tiene
    comandos propios que conviene habilitar. Se edita en ``opencode.json``.

    :returns: Bloque ``permission`` para la configuración.
    """
    return dict(PERMISOS_BASE)
