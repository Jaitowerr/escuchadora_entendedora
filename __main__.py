# __main__.py
import math
import multiprocessing as mp
import os
import time

import sounddevice as sd
import soundfile as sf

from escuchadora import Escuchadora
from micro import Microfono
import numpy as np


DURACION_MANUAL = 5
DURACION_AUTOMATICA = 3
TIEMPO_LIMITE = 6
UMBRAL_SILENCIO = 0.0001


def trabajo_grabacion(
    microfono: Microfono,
    segundos: int,
    ruta: str,
) -> None:
    """Graba un micrófono dentro de un proceso independiente."""
    resultado = microfono.grabar(
        segundos=segundos,
        ruta=ruta,
    )
    raise SystemExit(0 if resultado else 1)


def reproducir_audio(ruta: str) -> None:
    """Reproduce un WAV aumentando su volumen para poder comprobarlo."""
    try:
        audio, frecuencia = sf.read(ruta)

        pico = float(np.max(np.abs(audio)))

        if pico > 0:
            audio = audio / pico * 0.5

        print(f"Reproduciendo {ruta}...")
        sd.play(audio, frecuencia)
        sd.wait()
        print("Reproducción terminada.")

    except Exception as error:
        print(f"No se pudo reproducir el audio: {error}")


def medir_rms(ruta: str) -> float:
    """Calcula el nivel RMS de un archivo de audio."""
    audio, _ = sf.read(ruta)

    if len(audio) == 0:
        return 0.0

    suma = 0.0
    cantidad_muestras = 0

    for muestra in audio:
        if hasattr(muestra, "__iter__"):
            for canal in muestra:
                suma += float(canal) ** 2
                cantidad_muestras += 1
        else:
            suma += float(muestra) ** 2
            cantidad_muestras += 1

    if cantidad_muestras == 0:
        return 0.0

    return math.sqrt(suma / cantidad_muestras)


def fase_manual(escuchadora: Escuchadora) -> None:
    """Permite probar manualmente cada micrófono."""
    print("\n" + "=" * 60)
    print("PRUEBA MANUAL")
    print("=" * 60)
    print("Escribe un índice para probar un micrófono.")
    print("El audio se reproducirá después de grabarlo.")
    print("Escribe 'q' para pasar a la prueba automática.\n")

    while True:
        entrada = input(
            "Índice del micrófono o 'q' para continuar: "
        ).strip().lower()

        if entrada == "q":
            return

        if not entrada.isdigit():
            print("Escribe un índice válido o 'q'.")
            continue

        indice = int(entrada)

        microfono = next(
            (
                microfono
                for microfono in escuchadora.microfonos
                if microfono.indice == indice
            ),
            None,
        )

        if microfono is None:
            print("Ese índice no está en la lista.")
            continue

        ruta = f"manual_{indice}.wav"

        print(
            f"\nProbando [{indice}] {microfono.nombre}"
        )

        resultado = microfono.grabar(
            segundos=DURACION_MANUAL,
            ruta=ruta,
        )

        if not resultado:
            print("La grabación ha fallado.")
            continue

        reproducir_audio(ruta)

        respuesta = input(
            "¿Se escucha correctamente? (1 = sí, 0 = no): "
        ).strip()

        if respuesta == "1":
            print(f"Micrófono [{indice}] confirmado manualmente.")
        else:
            print(f"Micrófono [{indice}] descartado manualmente.")


def grabar_todos(
    escuchadora: Escuchadora,
) -> dict[int, str]:
    """Graba todos los micrófonos al mismo tiempo."""
    procesos: dict[int, mp.Process] = {}

    for microfono in escuchadora.microfonos:
        ruta = f"prueba_{microfono.indice}.wav"

        if os.path.exists(ruta):
            os.remove(ruta)

        proceso = mp.Process(
            target=trabajo_grabacion,
            args=(microfono, DURACION_AUTOMATICA, ruta),
        )

        procesos[microfono.indice] = proceso
        proceso.start()

    estados: dict[int, str] = {}
    limite = time.monotonic() + TIEMPO_LIMITE

    for indice, proceso in procesos.items():
        tiempo_restante = limite - time.monotonic()

        proceso.join(
            timeout=max(0.1, tiempo_restante)
        )

        if proceso.is_alive():
            proceso.terminate()
            proceso.join()
            estados[indice] = "BLOQUEADO"
        elif proceso.exitcode == 0:
            estados[indice] = "OK"
        else:
            estados[indice] = "ERROR"

    return estados


def fase_automatica(escuchadora: Escuchadora) -> None:
    """Graba, mide, ordena y reproduce los candidatos."""
    print("\n" + "=" * 60)
    print("PRUEBA AUTOMÁTICA")
    print("=" * 60)
    print(
        f"Se grabarán los {len(escuchadora.microfonos)} micrófonos "
        f"durante {DURACION_AUTOMATICA} segundos."
    )
    print("Habla durante la prueba.\n")

    estados = grabar_todos(escuchadora)

    print("\nResultados de la grabación:")

    candidatos: list[tuple[Microfono, str, float]] = []

    for microfono in escuchadora.microfonos:
        indice = microfono.indice
        estado = estados[indice]
        ruta = f"prueba_{indice}.wav"

        print(
            f"  [{estado:^9}] "
            f"[{indice}] {microfono.nombre}"
        )

        if estado != "OK":
            continue

        if not os.path.exists(ruta):
            print("             No se encontró el archivo WAV.")
            continue

        rms = medir_rms(ruta)

        if rms <= UMBRAL_SILENCIO:
            print(f"             RMS={rms:.6f} - silencio")
            continue

        print(f"             RMS={rms:.6f} - sonido detectado")
        candidatos.append((microfono, ruta, rms))

    candidatos.sort(
        key=lambda candidato: candidato[2],
        reverse=True,
    )

    if not candidatos:
        print("\nNo se ha encontrado ningún micrófono con sonido.")
        return

    print("\nCandidatos ordenados por nivel de sonido:")

    for posicion, (microfono, _, rms) in enumerate(candidatos, start=1):
        print(
            f"  {posicion}. [{microfono.indice}] "
            f"{microfono.nombre} - RMS={rms:.6f}"
        )

    confirmados: list[Microfono] = []

    print("\nAhora se comprobarán los candidatos uno por uno.")

    for microfono, ruta, rms in candidatos:
        print(
            f"\nCandidato [{microfono.indice}] "
            f"{microfono.nombre}"
        )
        print(f"Nivel RMS: {rms:.6f}")

        reproducir_audio(ruta)

        respuesta = input(
            "¿Se escucha correctamente? (1 = sí, 0 = no): "
        ).strip()

        if respuesta == "1":
            confirmados.append(microfono)
            print("Micrófono confirmado.")

            if len(confirmados) == 2:
                print("Ya hay dos micrófonos confirmados.")
                break
        else:
            print("Micrófono descartado.")

    print("\nMicrófonos confirmados:")

    if not confirmados:
        print("  Ninguno.")

    for microfono in confirmados:
        print(
            f"  [{microfono.indice}] "
            f"{microfono.nombre}"
        )


def main() -> None:
    mp.freeze_support()

    escuchadora = Escuchadora()
    escuchadora.detectar_microfonos()
    escuchadora.mostrar_microfonos()

    if not escuchadora.microfonos:
        return

    fase_manual(escuchadora)
    fase_automatica(escuchadora)


if __name__ == "__main__":
    main()
