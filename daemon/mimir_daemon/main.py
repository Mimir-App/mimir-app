"""Legacy entry point — redirige a capture.

Mantenido para compatibilidad con instalaciones existentes.
"""

from .capture import main

if __name__ == "__main__":
    main()
