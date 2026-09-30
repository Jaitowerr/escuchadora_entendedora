# micro.py
from dataclasses import dataclass

import sounddevice as sd
import soundfile as sf


@dataclass
class Microfono:
    """Representa un dispositivo de entrada de audio."""

    indice: int
    nombre: str
    canales: int
    frecuencia: int

    def grabar(self, segundos: int, ruta: str) -> bool:
        """Graba unos segundos del dispositivo y los guarda como WAV."""
        print(
            f"Grabando {segundos} s desde [{self.indice}] {self.nombre}... ¡habla!"
        )
        try:
            audio = sd.rec(
                frames=int(segundos * self.frecuencia),
                samplerate=self.frecuencia,
                channels=self.canales,
                device=self.indice,
            )
            sd.wait()
            sf.write(ruta, audio, self.frecuencia)
        except sd.PortAudioError as error:
            print(
                f"  ERROR en [{self.indice}] {self.nombre!r}: no se pudo abrir"
                f" el stream ({self.canales} canales, {self.frecuencia} Hz)."
                f"\n  Detalle: {error}"
            )
            return False
        print(f"Audio guardado en {ruta}")
        return True
    