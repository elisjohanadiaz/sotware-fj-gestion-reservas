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


class Reserva(Entidad):
    def __init__(self, identificador, cliente, servicio, duracion, impuesto=0, descuento=0):
        super().__init__(identificador)
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise DatoInvalido("La reserva requiere un cliente y un servicio válidos.")
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = servicio.validar_parametros(duracion)
        self.__costo = servicio.calcular_costo(duracion, impuesto, descuento)
        self.__estado = "PENDIENTE"

    @property
    def estado(self):
        return self.__estado

    @property
    def costo(self):
        return self.__costo

    def confirmar(self):
        if self.estado != "PENDIENTE":
            raise OperacionNoPermitida("Solo se puede confirmar una reserva pendiente.")
        if not self.__servicio.disponible:
            raise ServicioNoDisponible("El servicio ya tiene una reserva activa.")
        self.__servicio.cambiar_disponibilidad(False)
        self.__estado = "CONFIRMADA"
        LOG.info("Reserva confirmada: %s", self.identificador)

    def cancelar(self):
        if self.estado not in ("PENDIENTE", "CONFIRMADA"):
            raise OperacionNoPermitida("No se puede cancelar una reserva cerrada.")
        if self.estado == "CONFIRMADA":
            self.__servicio.cambiar_disponibilidad(True)
        self.__estado = "CANCELADA"
        LOG.info("Reserva cancelada: %s", self.identificador)

    def finalizar(self):
        if self.estado != "CONFIRMADA":
            raise OperacionNoPermitida("Solo se puede finalizar una reserva confirmada.")
        self.__servicio.cambiar_disponibilidad(True)
        self.__estado = "FINALIZADA"
        LOG.info("Reserva finalizada: %s", self.identificador)

    def procesar(self):
        """Demuestra try/except/else/finally sin ocultar la causa del fallo."""
        try:
            self.confirmar()
        except ErrorSistema:
            LOG.exception("No se pudo procesar la reserva %s", self.identificador)
            raise
        else:
            return self.costo
        finally:
            LOG.info("Fin del intento de procesamiento: %s | %s", self.identificador, self.estado)

    def describir(self):
        return (f"{self.identificador} | {self.__cliente.nombre} | {self.__servicio.nombre} | "
                f"{self.__duracion} h | {self.estado} | Total: {self.costo}")


class SistemaGestion:
    def __init__(self):
        self.__clientes = []
        self.__servicios = []
        self.__reservas = []

    @property
    def clientes(self):
        return tuple(self.__clientes)

    @property
    def servicios(self):
        return tuple(self.__servicios)

    @property
    def reservas(self):
        return tuple(self.__reservas)

    @staticmethod
    def _buscar(lista, identificador):
        for objeto in lista:
            if objeto.identificador == identificador:
                return objeto
        raise DatoInvalido(f"No existe el identificador: {identificador}.")

    @staticmethod
    def _agregar(lista, objeto):
        if any(item.identificador == objeto.identificador for item in lista):
            raise DatoInvalido(f"Identificador duplicado: {objeto.identificador}.")
        lista.append(objeto)
        LOG.info("Registro creado: %s | %s", objeto.__class__.__name__, objeto.identificador)
        return objeto

    def registrar_cliente(self, identificador, nombre, correo, telefono):
        return self._agregar(self.__clientes, Cliente(identificador, nombre, correo, telefono))

    def registrar_servicio(self, servicio):
        if not isinstance(servicio, Servicio):
            raise DatoInvalido("Debe registrar un objeto de tipo Servicio.")
        return self._agregar(self.__servicios, servicio)

    def crear_reserva(self, identificador, cliente_id, servicio_id, duracion, impuesto=0, descuento=0):
        if any(r.identificador == identificador for r in self.__reservas):
            raise DatoInvalido("El identificador de la reserva ya existe.")
        cliente = self._buscar(self.__clientes, cliente_id)
        servicio = self._buscar(self.__servicios, servicio_id)
        reserva = Reserva(identificador, cliente, servicio, duracion, impuesto, descuento)
        reserva.procesar()
        return self._agregar(self.__reservas, reserva)

    def cancelar_reserva(self, identificador):
        self._buscar(self.__reservas, identificador).cancelar()
        return "Reserva cancelada correctamente."

    def finalizar_reserva(self, identificador):
        self._buscar(self.__reservas, identificador).finalizar()
        return "Reserva finalizada correctamente."

import sys


def simular_operaciones():
    """Usa un sistema independiente; no modifica los registros de la interfaz."""
    sistema = SistemaGestion()
    # Cada caso declara si debe fallar: un error previsto es un caso correcto.
    casos = [
        ("Registrar cliente válido", False,
         lambda: sistema.registrar_cliente("C1", "Ana Pérez", "ana@example.com", "3001234567")),
        ("Rechazar correo inválido", True,
         lambda: sistema.registrar_cliente("C2", "Luis", "correo-invalido", "3001234567")),
        ("Rechazar teléfono inválido", True,
         lambda: sistema.registrar_cliente("C2", "Luis", "luis@example.com", "abc")),
        ("Rechazar cliente duplicado", True,
         lambda: sistema.registrar_cliente("C1", "Ana Pérez", "ana@example.com", "3001234567")),
        ("Crear sala válida", False,
         lambda: sistema.registrar_servicio(ReservaSala("S1", "Sala Norte", 50000, 10))),
        ("Rechazar tarifa negativa", True,
         lambda: sistema.registrar_servicio(ReservaSala("S2", "Sala Sur", -1, 10))),
        ("Crear equipo válido", False,
         lambda: sistema.registrar_servicio(AlquilerEquipo("E1", "Portátil", 15000, "Computador"))),
        ("Crear asesoría válida", False,
         lambda: sistema.registrar_servicio(AsesoriaEspecializada("A1", "Soporte", 80000, "Software"))),
        ("Rechazar capacidad fraccionaria", True,
         lambda: sistema.registrar_servicio(ReservaSala("S2", "Sala Sur", 50000, "2.5"))),
        ("Controlar parámetros faltantes", True,
         lambda: sistema.registrar_cliente("C2", "Luis")),
        ("Confirmar reserva de sala", False,
         lambda: sistema.crear_reserva("R1", "C1", "S1", 2)),
        ("Rechazar servicio ocupado", True,
         lambda: sistema.crear_reserva("R2", "C1", "S1", 2)),
        ("Rechazar cliente inexistente", True,
         lambda: sistema.crear_reserva("R2", "NO_EXISTE", "E1", 2)),
        ("Rechazar duración cero", True,
         lambda: sistema.crear_reserva("R2", "C1", "E1", 0)),
        ("Cancelar y liberar sala", False, lambda: sistema.cancelar_reserva("R1")),
        ("Volver a reservar sala liberada", False,
         lambda: sistema.crear_reserva("R2", "C1", "S1", 3, "0.10", "0.05")),
        ("Rechazar segunda confirmación", True, lambda: sistema.reservas[-1].confirmar()),
        ("Finalizar y liberar sala", False, lambda: sistema.finalizar_reserva("R2")),
        ("Rechazar cancelación de reserva finalizada", True,
         lambda: sistema.cancelar_reserva("R2")),
        ("Rechazar descuento superior al 100%", True,
         lambda: sistema.crear_reserva("R3", "C1", "E1", 2, 0, "1.5")),
        ("Confirmar alquiler de equipo", False,
         lambda: sistema.crear_reserva("R3", "C1", "E1", 2)),
        ("Confirmar asesoría", False,
         lambda: sistema.crear_reserva("R4", "C1", "A1", "0.5")),
        ("Cálculo polimórfico con variantes opcionales", False,
         lambda: [(s.calcular_costo(2), s.calcular_costo(2, "0.10"),
                   s.calcular_costo(2, "0.10", "0.05")) for s in sistema.servicios]),
        ("Rechazar duración no finita", True,
         lambda: sistema.crear_reserva("R5", "C1", "S1", "NaN")),
    ]
    lineas = ["SIMULACIÓN DE SOFTWARE FJ (datos ficticios)"]
    aprobados = 0
    for indice, (nombre, debe_fallar, accion) in enumerate(casos, 1):
        try:
            resultado = accion()
        except Exception as error:
            # Frontera de la aplicación: registra incluso errores inesperados.
            LOG.exception("Simulación %s: %s", indice, nombre)
            correcto = debe_fallar and isinstance(error, (ErrorSistema, TypeError))
            detalle = f"{type(error).__name__}: {error}"
        else:
            correcto = not debe_fallar
            detalle = resultado.describir() if hasattr(resultado, "describir") else str(resultado)
        finally:
            LOG.info("Simulación: operación %s terminada", indice)
        aprobados += int(correcto)
        lineas.append(f"{indice:02d}. {'OK' if correcto else 'FALLO'} | {nombre}\n    {detalle}")
    lineas.append(f"\nResultado: {aprobados}/{len(casos)} casos con comportamiento esperado.")
    return "\n".join(lineas), aprobados == len(casos)


def abrir_interfaz():
    # Importación diferida: --demo no requiere una pantalla ni cargar Tkinter.
    import tkinter as tk
    from tkinter import ttk, messagebox
    from tkinter.scrolledtext import ScrolledText

    class Aplicacion:
        def __init__(self, ventana):
            self.sistema = SistemaGestion()
            self.ventana = ventana
            ventana.title("Software FJ - Clientes, servicios y reservas")
            ventana.geometry("980x760")
            ventana.minsize(820, 650)
            ventana.columnconfigure(0, weight=1)
            ventana.rowconfigure(2, weight=1)
            ttk.Label(ventana, text="Software FJ", font=("Arial", 20, "bold")).grid(
                row=0, column=0, sticky="w", padx=18, pady=10)
            pestañas = ttk.Notebook(ventana)
            pestañas.grid(row=1, column=0, sticky="ew", padx=18)
            self.c = self.formulario(pestañas, "Clientes", [
                ("Identificador", ""), ("Nombre", ""), ("Correo", ""), ("Teléfono", "")])
            ttk.Button(self.c["panel"], text="Registrar cliente", command=lambda: self.ejecutar(
                lambda: self.sistema.registrar_cliente(*self.valores(self.c)))).grid(
                    row=5, column=0, columnspan=2, pady=8)
            self.s = self.formulario(pestañas, "Servicios", [
                ("Identificador", ""), ("Nombre", ""), ("Tarifa por hora", ""),
                ("Capacidad / tipo / especialidad", "")])
            ttk.Label(self.s["panel"], text="Tipo de servicio").grid(row=5, column=0, sticky="w")
            self.tipo = ttk.Combobox(self.s["panel"], values=("Sala", "Equipo", "Asesoría"), state="readonly")
            self.tipo.set("Sala")
            self.tipo.grid(row=5, column=1, sticky="ew")
            ttk.Button(self.s["panel"], text="Registrar servicio", command=lambda: self.ejecutar(
                self.registrar_servicio)).grid(row=6, column=0, columnspan=2, pady=8)
            self.r = self.formulario(pestañas, "Reservas", [
                ("Identificador de reserva", ""), ("Identificador de cliente", ""),
                ("Identificador de servicio", ""), ("Duración en horas", "2"),
                ("Impuesto (0 a 1)", "0"), ("Descuento (0 a 1)", "0")])
            acciones = ttk.Frame(self.r["panel"])
            acciones.grid(row=7, column=0, columnspan=2, pady=8)
            ttk.Button(acciones, text="Crear y confirmar", command=lambda: self.ejecutar(
                lambda: self.sistema.crear_reserva(*self.valores(self.r)))).pack(side="left", padx=4)
            ttk.Button(acciones, text="Cancelar", command=lambda: self.ejecutar(
                lambda: self.sistema.cancelar_reserva(self.valores(self.r)[0]))).pack(side="left", padx=4)
            ttk.Button(acciones, text="Finalizar", command=lambda: self.ejecutar(
                lambda: self.sistema.finalizar_reserva(self.valores(self.r)[0]))).pack(side="left", padx=4)
            self.salida = ScrolledText(ventana, wrap="word", height=15, font=("Consolas", 10))
            self.salida.grid(row=2, column=0, sticky="nsew", padx=18, pady=12)
            controles = ttk.Frame(ventana)
            controles.grid(row=3, column=0, pady=(0, 12))
            ttk.Button(controles, text="Ver todos los registros", command=self.listar).pack(side="left", padx=5)
            ttk.Button(controles, text="Simular 24 operaciones", command=lambda: self.ejecutar(
                lambda: simular_operaciones()[0])).pack(side="left", padx=5)
            ttk.Label(ventana, text="Datos en memoria: se eliminan al cerrar. Solo los eventos y errores se guardan en eventos.log.").grid(
                row=4, column=0, padx=12, pady=(0, 8))
            self.escribir("Registre un cliente y un servicio; luego cree una reserva.\n"
                          "Sala: capacidad entera. Equipo: tipo de equipo. Asesoría: especialidad.\n"
                          "Los impuestos y descuentos son tasas configurables de ejemplo, no tarifas legales.")

        @staticmethod
        def formulario(pestañas, titulo, campos):
            panel = ttk.Frame(pestañas, padding=12)
            panel.columnconfigure(1, weight=1)
            pestañas.add(panel, text=titulo)
            entradas = []
            for fila, (nombre, valor) in enumerate(campos):
                ttk.Label(panel, text=nombre).grid(row=fila, column=0, sticky="w", padx=(0, 15), pady=3)
                entrada = ttk.Entry(panel, width=55)
                entrada.insert(0, valor)
                entrada.grid(row=fila, column=1, sticky="ew", pady=3)
                entradas.append(entrada)
            return {"panel": panel, "entradas": entradas}

        @staticmethod
        def valores(formulario):
            return [entrada.get().strip() for entrada in formulario["entradas"]]

        def escribir(self, texto):
            self.salida.delete("1.0", tk.END)
            self.salida.insert(tk.END, texto)

        def ejecutar(self, accion):
            try:
                resultado = accion()
            except Exception as error:
                LOG.exception("Operación de la interfaz rechazada")
                mensaje = str(error) if isinstance(error, ErrorSistema) else "Error inesperado; consulte eventos.log."
                self.escribir(f"Operación no realizada: {mensaje}\nPuede corregir los datos y continuar.")
                messagebox.showerror("Operación no realizada", mensaje)
            else:
                texto_resultado = resultado.describir() if hasattr(resultado, "describir") else str(resultado)
                self.escribir(texto_resultado)
            finally:
                LOG.info("Interfaz lista para la siguiente operación")

        def registrar_servicio(self):
            constructores = {"Sala": ReservaSala, "Equipo": AlquilerEquipo, "Asesoría": AsesoriaEspecializada}
            return self.sistema.registrar_servicio(constructores[self.tipo.get()](*self.valores(self.s)))

        def listar(self):
            lineas = []
            for titulo, registros in (("CLIENTES", self.sistema.clientes),
                                      ("SERVICIOS", self.sistema.servicios), ("RESERVAS", self.sistema.reservas)):
                lineas.append(f"\n{titulo}")
                # Polimorfismo sobre las entidades del sistema.
                lineas.extend(objeto.describir() for objeto in registros)
                if not registros:
                    lineas.append("Sin registros.")
            self.escribir("\n".join(lineas))

    raiz = tk.Tk()
    Aplicacion(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    try:
        ruta = configurar_log()
    except OSError as error:
        print(f"No se puede crear eventos.log: {error}. Mueva el proyecto a una carpeta con permiso de escritura.")
        sys.exit(1)
    LOG.info("Inicio de Software FJ")
    if "--demo" in sys.argv:
        reporte, correcto = simular_operaciones()
        print(reporte)
        print(f"\nRegistro de eventos: {ruta}")
        sys.exit(0 if correcto else 1)
    else:
        abrir_interfaz()
        
