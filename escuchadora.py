from dataclasses import dataclass

import sounddevice as sd
from micro import Microfono


class Escuchadora:
    """Clase principal: detecta y gestiona los micrófonos."""

    def __init__(self) -> None:
        self.microfonos: list[Microfono] = []

    @staticmethod
    def es_microfono_valido(dispositivo: dict) -> bool:
        """Indica si una entrada puede tratarse como micrófono."""
        nombre = dispositivo["name"].lower()
        es_entrada = dispositivo["max_input_channels"] > 0
        es_mezcla = "mezcla estéreo" in nombre or "stereo mix" in nombre
        # "Input (...)" sin nombre propio: endpoints Bluetooth de móviles
        # (bthhfenum.sys) o entradas fantasma tipo "Input ()".
        es_entrada_generica = nombre.startswith("input (")
        return es_entrada and not es_mezcla and not es_entrada_generica

    def detectar_microfonos(self) -> list[Microfono]:
        """Enumera solo las entradas válidas para capturar voz."""
        self.microfonos = []
        for indice, dispositivo in enumerate(sd.query_devices()):
            if self.es_microfono_valido(dispositivo):
                self.microfonos.append(
                    Microfono(
                        indice=indice,
                        nombre=dispositivo["name"],
                        canales=dispositivo["max_input_channels"],
                        frecuencia=int(dispositivo["default_samplerate"]),
                    )
                )
        return self.microfonos

    def mostrar_microfonos(self) -> None:
        """Imprime por terminal los micrófonos detectados."""
        if not self.microfonos:
            print("No se ha detectado ningún micrófono.")
            return

        print(f"Micrófonos disponibles: {len(self.microfonos)}")
        for microfono in self.microfonos:
            print(
                f"  [{microfono.indice}] {microfono.nombre} "
                f"({microfono.canales} canales, {microfono.frecuencia} Hz)"
            )
            