"""Recocido simulado discreto propio con movimientos que conservan recursos."""
import math
import numpy as np
from .modelo import simular, validar_dotacion


def optimizar(base, llamadas_ajuste, disponibilidad, semilla=7301, iteraciones=500,
              temperatura_inicial=2.0, temperatura_final=.02):
    validar_dotacion(base)
    if not llamadas_ajuste:
        raise ValueError('Se requiere al menos una entrada de ajuste para evaluar candidatas')
    if iteraciones<1 or not 0<temperatura_final<=temperatura_inicial:
        raise ValueError('Parámetros de recocido inválidos')
    rng=np.random.default_rng(semilla)
    inferiores=[max(1,int(c)-2) for c in base]
    superiores=[min(9,int(c)+2) for c in base]
    cache={}
    def evaluar(c):
        key=tuple(c)
        if key not in cache:
            cache[key]=float(np.mean([100-simular(d,c,disponibilidad)['metricas']['sla_pct'] for d in llamadas_ajuste]))
        return cache[key]
    def movimientos(c):
        # Un solo traslado de una hora-agente entre franjas: factibilidad exacta.
        return [(i,j) for i in range(17) for j in range(17) if i!=j and c[i]>inferiores[i] and c[j]<superiores[j]]
    actual=list(base); costo=evaluar(actual); mejor=actual.copy(); mejor_costo=costo
    registro=[]
    # Sin pares factibles desde la base (p. ej. todas las franjas en 1 o en 9) no hay busqueda posible.
    factible=bool(movimientos(actual))
    terminacion='iteraciones completadas' if factible else 'sin movimientos factibles'
    for k in range(iteraciones if factible else 0):
        t=temperatura_inicial*(temperatura_final/temperatura_inicial)**(k/max(1,iteraciones-1))
        candidato=actual.copy()
        pares=movimientos(candidato)
        i,j=pares[int(rng.integers(len(pares)))]; candidato[i]-=1;candidato[j]+=1
        validar_dotacion(candidato,sum(base))
        c=evaluar(candidato); delta=c-costo
        acepta=delta<=0 or rng.random()<math.exp(-delta/t)
        if acepta:actual,costo=candidato,c
        if costo<mejor_costo:mejor,mejor_costo=actual.copy(),costo
        registro.append(dict(iteracion=k+1,temperatura=t,costo_actual=costo,mejor_costo=mejor_costo,
            aceptado=bool(acepta),origen_hora=i+7,destino_hora=j+7,evaluaciones=len(cache)))
    assert all(a<=c<=b for a,c,b in zip(inferiores,mejor,superiores))
    return dict(dotacion=mejor,costo=mejor_costo,costo_base=evaluar(base),traza=registro,
                limites_inferiores=inferiores,limites_superiores=superiores,
                semilla=semilla,iteraciones=iteraciones,evaluaciones=len(cache),terminacion=terminacion)
