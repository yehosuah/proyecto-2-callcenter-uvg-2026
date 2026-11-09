"""Recalcula estadísticas y comprueba semillas, restricciones y hashes guardados."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experimentos import resumen, METRICAS
from src.modelo import validar_dotacion


def main():
    r=json.loads((ROOT/'resultados/resumen.json').read_text())
    man=json.loads((ROOT/'resultados/manifiesto.json').read_text())
    runs=pd.read_csv(ROOT/'resultados/repeticiones.csv')
    dif=pd.read_csv(ROOT/'resultados/diferencias_pareadas.csv')
    assert len(runs)==10*r['repeticiones']==600
    assert not runs.duplicated(['escenario','politica','semilla']).any()
    for _,g in runs.groupby(['escenario','politica']):
        assert len(g)==60 and sorted(g.semilla)==man['semillas_evaluacion']
    for etapa in ['semillas_calibracion','semillas_busqueda','semillas_optimizador']:
        assert not set(man[etapa])&set(man['semillas_evaluacion'])
    base=r['parametros']['dotacion_base'];opt=r['dotacion_mejorada']
    validar_dotacion(opt,sum(base));assert sum(base)==sum(opt)==105
    assert all(abs(b-o)<=2 for b,o in zip(base,opt))
    assert runs.fecha_referencia.str.startswith('1999-12').all()
    assert (runs.llamadas==runs.atendidas+runs.abandonadas).all()
    for escenario,g in runs.groupby('escenario'):
        b=g[g.politica=='base'].set_index('semilla').sort_index()
        o=g[g.politica=='mejorada'].set_index('semilla').sort_index()
        assert b.llamadas.equals(o.llamadas)
        assert b.fecha_referencia.equals(o.fecha_referencia)
        for m in METRICAS:
            recomputado=resumen(o[m]-b[m])
            guardado=dif[(dif.escenario==escenario)&(dif.metrica==m)].iloc[0]
            for k in ['media','sd','ic95_inf','ic95_sup']:
                assert np.isclose(recomputado[k],guardado[k],atol=1e-10), (escenario,m,k)
    for nombre,sha in man['hashes_datos'].items():
        assert hashlib.sha256((ROOT/'datos'/nombre).read_bytes()).hexdigest()==sha,nombre
    datos=pd.read_csv(ROOT/'datos/llamadas_sin_identificadores.csv')
    assert len(datos)==67563 and datos.fecha.nunique()==44
    assert not {'customer_id','call_id','server','vru+line'}&set(datos.columns)
    v=pd.read_csv(ROOT/'resultados/validacion_por_dia.csv')
    assert len(v)==66 and v.fecha.nunique()==22
    for metrica,g in v.groupby('metrica'):
        assert np.isclose(g.error.abs().mean(),r['mae_diario'][metrica])
    equipo=json.loads((ROOT/'equipo.json').read_text())
    assert [p['carne'] for p in equipo['integrantes']]==['23427','231977','241452']
    print('OK: 600 corridas, 60 réplicas por condición/política, IC pareados, semillas separadas, 105 horas nominales, restricciones, datos y equipo.')
    print('La validación numérica no acredita contribuciones, aprobación docente ni publicación en GitHub.')


if __name__=='__main__':main()
