#Sofware FJ
#Integrated Management System for Clients, Services and Reservations

from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from pathlib import Path
import logging
import re


# Solo se escriben eventos y errores. Los datos del negocio viven en listas.
LOG = logging.getLogger("software_fj")
LOG.addHandler(logging.NullHandler())


def configurar_log(ruta=None):
    """El archivo se crea junto al programa, salvo una ruta explícita."""
    destino = Path(ruta) if ruta else Path(__file__).with_name("eventos.log")
    manejador = logging.FileHandler(destino, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    for anterior in list(LOG.handlers):
        LOG.removeHandler(anterior)
        anterior.close()
    LOG.addHandler(manejador)
    LOG.setLevel(logging.INFO)
    return destino


class ErrorSistema(Exception):
    """Cada excepción del dominio registra su mensaje al construirse."""
    def __init__(self, mensaje):
        super().__init__(mensaje)
        LOG.error("%s: %s", self.__class__.__name__, mensaje)


class DatoInvalido(ErrorSistema):
    pass


class OperacionNoPermitida(ErrorSistema):
    pass


class ServicioNoDisponible(ErrorSistema):
    pass


def texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalido(f"{campo}: el texto es obligatorio.")
    if len(valor.strip()) > 150:
        raise DatoInvalido(f"{campo}: máximo 150 caracteres.")
    return valor.strip()


def numero(valor, campo, minimo=Decimal("0"), maximo=Decimal("1000000000")):
    """Convierte decimales con punto/coma y encadena el error original."""
    try:
        if isinstance(valor, bool):
            raise ValueError("Un booleano no es un número de negocio.")
        resultado = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError) as causa:
        raise DatoInvalido(f"{campo}: debe ingresar un número.") from causa
    if not resultado.is_finite() or not minimo <= resultado <= maximo:
        raise DatoInvalido(f"{campo}: valor permitido entre {minimo} y {maximo}.")
    return resultado


class Entidad(ABC):
    """Abstracción general compartida por clientes, servicios y reservas."""
    def __init__(self, identificador):
        self.__identificador = texto(identificador, "Identificador")

    @property
    def identificador(self):
        return self.__identificador

    @abstractmethod
    def describir(self):
        pass


class Cliente(Entidad):
    """Datos privados y propiedades de solo lectura para su encapsulación."""
    def __init__(self, identificador, nombre, correo, telefono):
        super().__init__(identificador)
        self.__nombre = texto(nombre, "Nombre")
        self.__correo = texto(correo, "Correo")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.__correo):
            raise DatoInvalido("Correo: formato inválido.")
        self.__telefono = texto(telefono, "Teléfono")
        if not re.fullmatch(r"\+?[0-9]{7,15}", self.__telefono):
            raise DatoInvalido("Teléfono: use entre 7 y 15 dígitos; se admite + al inicio.")

    @property
    def nombre(self):
        return self.__nombre

    @property
    def correo(self):
        return self.__correo

    @property
    def telefono(self):
        return self.__telefono

    def describir(self):
        return f"{self.identificador} | {self.nombre} | {self.correo} | {self.telefono}"
