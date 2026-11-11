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

from abc import abstractmethod
from decimal import Decimal, ROUND_HALF_UP


class Servicio(Entidad):
    def __init__(self, identificador, nombre, tarifa):
        super().__init__(identificador)
        self.__nombre = texto(nombre, "Nombre del servicio")
        self.__tarifa = numero(tarifa, "Tarifa por hora", Decimal("0.01"))
        self.__disponible = True

    @property
    def nombre(self):
        return self.__nombre

    @property
    def tarifa(self):
        return self.__tarifa

    @property
    def disponible(self):
        return self.__disponible

    def cambiar_disponibilidad(self, valor):
        if not isinstance(valor, bool):
            raise DatoInvalido("Disponibilidad: se requiere True o False.")
        self.__disponible = valor

    @abstractmethod
    def validar_parametros(self, duracion):
        pass

    @abstractmethod
    def calcular_costo(self, duracion, impuesto=0, descuento=0):
        """Parámetros opcionales para simular variantes de sobrecarga en Python."""

    def _total(self, base, impuesto, descuento):
        tasa = numero(impuesto, "Impuesto", maximo=Decimal("1"))
        rebaja = numero(descuento, "Descuento", maximo=Decimal("1"))
        total = base * (1 - rebaja) * (1 + tasa)
        if not total.is_finite() or total < 0:
            raise DatoInvalido("El cálculo produjo un costo inconsistente.")
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ReservaSala(Servicio):
    def __init__(self, identificador, nombre, tarifa, capacidad):
        super().__init__(identificador, nombre, tarifa)
        cantidad = numero(capacidad, "Capacidad", Decimal("1"), Decimal("1000"))
        if cantidad != cantidad.to_integral_value():
            raise DatoInvalido("Capacidad: debe ser un número entero.")
        self.capacidad = int(cantidad)

    def validar_parametros(self, duracion):
        return numero(duracion, "Horas de sala", Decimal("1"), Decimal("12"))

    def calcular_costo(self, duracion, impuesto=0, descuento=0):
        return self._total(self.tarifa * self.validar_parametros(duracion), impuesto, descuento)

    def describir(self):
        return f"Sala: {self.nombre} | capacidad {self.capacidad} | {self.tarifa}/hora"


class AlquilerEquipo(Servicio):
    def __init__(self, identificador, nombre, tarifa, tipo_equipo):
        super().__init__(identificador, nombre, tarifa)
        self.tipo_equipo = texto(tipo_equipo, "Tipo de equipo")

    def validar_parametros(self, duracion):
        return numero(duracion, "Horas de alquiler", Decimal("1"), Decimal("168"))

    def calcular_costo(self, duracion, impuesto=0, descuento=0):
        return self._total(self.tarifa * self.validar_parametros(duracion), impuesto, descuento)

    def describir(self):
        return f"Equipo: {self.nombre} | tipo {self.tipo_equipo} | {self.tarifa}/hora"


class AsesoriaEspecializada(Servicio):
    def __init__(self, identificador, nombre, tarifa, especialidad):
        super().__init__(identificador, nombre, tarifa)
        self.especialidad = texto(especialidad, "Especialidad")

    def validar_parametros(self, duracion):
        return numero(duracion, "Horas de asesoría", Decimal("0.5"), Decimal("8"))

    def calcular_costo(self, duracion, impuesto=0, descuento=0):
        return self._total(self.tarifa * self.validar_parametros(duracion), impuesto, descuento)

    def describir(self):
        return f"Asesoría: {self.nombre} | {self.especialidad} | {self.tarifa}/hora"

