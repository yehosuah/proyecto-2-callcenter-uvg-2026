"""Motor de eventos discretos propio. Tiempo en segundos desde las 07:00."""
from dataclasses import dataclass
import heapq
import math
import numpy as np

HORA = 3600.0
HORIZONTE = 17 * HORA


@dataclass(frozen=True)
class Llamada:
    llegada: float
    servicio: float
    paciencia: float
    prioritaria: bool = False
    tipo: str = "PS"


def validar_dotacion(dotacion, presupuesto=None, maximo=9):
    if len(dotacion) != 17:
        raise ValueError("Se requieren 17 capacidades horarias, de 07:00 a 24:00")
    if any(isinstance(c, bool) or int(c) != c or not 1 <= c <= maximo for c in dotacion):
        raise ValueError("La capacidad debe ser entera y estar entre 1 y 9")
    if presupuesto is not None and sum(dotacion) != presupuesto:
        raise ValueError("La propuesta cambia el presupuesto de horas-agente")
    return True


def validar_semilla(semilla):
    if isinstance(semilla, bool) or not isinstance(semilla, (int, np.integer)) or semilla < 0:
        raise ValueError("La semilla debe ser un entero no negativo")
    return int(semilla)


def validar_factores(demanda, servicio_factor):
    if not (math.isfinite(demanda) and math.isfinite(servicio_factor)) or demanda < 0 or servicio_factor <= 0:
        raise ValueError("Los factores de demanda y servicio deben ser finitos, con demanda >= 0 y servicio > 0")
    return True


def generar_llamadas(parametros, semilla, demanda=1.0, servicio_factor=1.0):
    validar_factores(demanda, servicio_factor)
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(validar_semilla(semilla)).spawn(5)]
    ra, rt, rs, rp, rr = streams
    cv2 = parametros["cv2_demanda_diaria"]
    factor = ra.gamma(1 / cv2, cv2) if cv2 > 0 else 1.0
    llegadas = []
    for h, tasa in enumerate(parametros["llegadas_hora"]):
        n = ra.poisson(tasa * demanda * factor)
        llegadas.extend(h * HORA + ra.uniform(0, HORA, int(n)))
    llegadas.sort()
    tipos = list(parametros["servicio"])
    pesos = [parametros["mezcla_tipos"][t] for t in tipos]
    muestras_tipo = rt.choice(tipos, size=len(llegadas), p=pesos)
    normales = rs.normal(size=len(llegadas))
    paciencia = rp.exponential(parametros["paciencia_media_s"], size=len(llegadas))
    prioridad = rr.uniform(size=len(llegadas)) < parametros["fraccion_prioritaria"]
    return [Llamada(float(t), float(math.exp(parametros["servicio"][k]["mu"] +
                   parametros["servicio"][k]["sigma"] * z) * servicio_factor),
                   float(p), bool(q), str(k))
            for t, k, z, p, q in zip(llegadas, muestras_tipo, normales, paciencia, prioridad)]


def generar_replay(dias, parametros, semilla, demanda=1.0, servicio_factor=1.0):
    """Sortea uniformemente un día real; servicio/paciencia siguen siendo simulados.

    Para sensibilidad, reduce entradas por thinning o agrega una superposición
    bootstrap de llegadas del mismo día. La nueva demanda es sintética.
    """
    validar_factores(demanda, servicio_factor)
    ra,rs,rp,rr=[np.random.default_rng(s) for s in np.random.SeedSequence(validar_semilla(semilla)).spawn(4)]
    fechas=sorted(dias)
    fecha=fechas[int(ra.integers(len(fechas)))]; filas=list(dias[fecha])
    if demanda<1:
        filas=[r for r in filas if ra.random()<demanda]
    elif demanda>1:
        n=ra.poisson((demanda-1)*len(filas))
        extras=[filas[int(i)] for i in ra.integers(0,len(filas),int(n))]
        filas=filas+extras
    filas.sort(key=lambda r:r[0])
    z=rs.normal(size=len(filas)); p=rp.exponential(parametros['paciencia_media_s'],size=len(filas))
    pr=rr.uniform(size=len(filas))<parametros['fraccion_prioritaria']
    llamadas=[Llamada(float(a),float(math.exp(parametros['servicio'][k]['mu']+
        parametros['servicio'][k]['sigma']*zz)*servicio_factor),float(pp),bool(q),k)
        for (a,k),zz,pp,q in zip(filas,z,p,pr)]
    return fecha,llamadas


def simular(llamadas, dotacion, disponibilidad=1.0, umbral_s=120.0, traza=False):
    """No se interrumpe un servicio al disminuir capacidad. Se vacía al cierre.

    En empates: terminaciones, cambios de capacidad, llegadas, abandonos.
    Una terminación exactamente al vencer la paciencia permite atención.
    La capacidad final se conserva para vaciar; se informa el tiempo extra.
    """
    validar_dotacion(dotacion)
    if not (math.isfinite(disponibilidad) and 0 < disponibilidad <= 1 and math.isfinite(umbral_s) and umbral_s > 0):
        raise ValueError("Disponibilidad o umbral inválido: deben ser finitos, 0 < disponibilidad <= 1 y umbral > 0")
    for c in llamadas:
        if not (0 <= c.llegada < HORIZONTE and c.servicio > 0 and c.paciencia >= 0):
            raise ValueError("Llamada fuera del horizonte o con duración inválida")
        if not all(math.isfinite(v) for v in (c.llegada, c.servicio, c.paciencia)):
            raise ValueError("Valores no finitos")
    n = len(llamadas)
    estado = np.zeros(n, dtype=np.int8)  # 0 futura, 1 cola, 2 servicio, 3 terminada, 4 abandono
    esperas = np.zeros(n)
    inicios = np.full(n, np.nan)
    eventos = [(c.llegada, 2, i) for i, c in enumerate(llamadas)]
    eventos += [(h * HORA, 1, h) for h in range(1, 17)]
    heapq.heapify(eventos)
    cola = []
    ocupados = en_cola = 0
    capacidad = int(dotacion[0])
    anterior = area_cola = trabajo = trabajo_apertura = 0.0
    ultimo_fin = 0.0
    historial = []

    def atender(t):
        nonlocal ocupados, en_cola
        while ocupados < capacidad and cola:
            _, i = heapq.heappop(cola)
            if estado[i] != 1:
                continue
            estado[i] = 2
            en_cola -= 1
            ocupados += 1
            inicios[i] = t
            esperas[i] = t - llamadas[i].llegada
            heapq.heappush(eventos, (t + llamadas[i].servicio / disponibilidad, 0, i))

    while eventos:
        t, evento, i = heapq.heappop(eventos)
        area_cola += en_cola * (t - anterior)
        trabajo += ocupados * (t - anterior)
        trabajo_apertura += ocupados * max(0, min(t, HORIZONTE) - min(anterior, HORIZONTE))
        anterior = t
        if evento == 0:
            if estado[i] != 2:
                raise AssertionError("Terminación sin servicio activo")
            estado[i] = 3
            ocupados -= 1
            ultimo_fin = max(ultimo_fin, t)
        elif evento == 1:
            capacidad = int(dotacion[i])
        elif evento == 2:
            estado[i] = 1
            en_cola += 1
            c = llamadas[i]
            heapq.heappush(cola, (c.llegada - 90 * c.prioritaria, i))
            heapq.heappush(eventos, (c.llegada + c.paciencia, 3, i))
        elif estado[i] == 1:
            estado[i] = 4
            esperas[i] = t - llamadas[i].llegada
            en_cola -= 1
        atender(t)
        if traza:
            historial.append([round(t, 6), en_cola, ocupados, capacidad])
    atendidas = estado == 3
    abandonadas = estado == 4
    if not (int(atendidas.sum() + abandonadas.sum()) == n and ocupados == 0 and en_cola == 0):
        raise AssertionError("No se conserva el número de llamadas")
    if not math.isclose(area_cola, float(esperas.sum()), rel_tol=1e-8, abs_tol=1e-6):
        raise AssertionError("Área de cola distinta de la suma de esperas")
    sla = float(np.mean(atendidas & (esperas <= umbral_s))) if n else 0.0
    m = dict(llamadas=n, atendidas=int(atendidas.sum()), abandonadas=int(abandonadas.sum()),
             sla_pct=100 * sla, abandono_pct=100 * float(abandonadas.mean()) if n else 0.0,
             espera_media_s=float(esperas.mean()) if n else 0.0,
             espera_atendidas_s=float(esperas[atendidas].mean()) if atendidas.any() else 0.0,
             p90_espera_s=float(np.quantile(esperas, .9)) if n else 0.0,
             horas_agente=sum(dotacion), trabajo_horas=trabajo/HORA,
             utilizacion_pct=100 * trabajo_apertura/(sum(dotacion)*HORA),
             extra_min=max(0, ultimo_fin-HORIZONTE)/60,
             cola_media=area_cola/HORIZONTE)
    salida = {"metricas": m}
    if traza:
        salida.update(traza=historial, llamadas=[dict(llegada=c.llegada, servicio=c.servicio,
                      paciencia=c.paciencia, prioritaria=c.prioritaria, tipo=c.tipo,
                      espera=float(esperas[i]), atendida=bool(atendidas[i]))
                      for i, c in enumerate(llamadas)])
    return salida
