"""Recalcula estadísticas y comprueba semillas, restricciones y hashes guardados.

Los conteos esperados (réplicas, corridas, diferencias pareadas) se toman del
resumen y del manifiesto de la carpeta verificada; no hay números de réplicas
escritos en este archivo. Un conjunto incompleto o mezclado debe fallar.

Uso:
    python scripts/verificar_entrega.py                      # entrega: resultados/ + documentos
    python scripts/verificar_entrega.py --resultados otra    # solo la evidencia de otra corrida
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experimentos import resumen, METRICAS, ESCENARIOS
from src.modelo import validar_dotacion

POLITICAS=('base','mejorada')
MINIMO_REPLICAS=30
HORAS_NOMINALES=105
VARIACION_MAXIMA=2
METRICAS_VALIDACION=['llamadas','sla_pct','abandono_pct','espera_media_s','espera_atendidas_s','p90_espera_s']
METRICAS_DIARIAS=['sla_pct','abandono_pct','espera_media_s']
CAMPOS_IC=['media','sd','ic95_inf','ic95_sup']
ARCHIVOS=['resumen.json','manifiesto.json','demo.json','repeticiones.csv','resumen.csv',
          'diferencias_pareadas.csv','validacion.csv','validacion_por_dia.csv','referencia_diaria.csv']


class EvidenciaInvalida(Exception):
    """La carpeta de resultados no es un conjunto completo y coherente."""


def exigir(condicion,mensaje):
    # Comprobaciones explícitas: `assert` desaparece con python -O.
    if not condicion:raise EvidenciaInvalida(mensaje)


def leer_json(ruta):return json.loads(Path(ruta).read_text(encoding='utf-8'))


def cercano(a,b):return bool(np.isclose(float(a),float(b),rtol=1e-9,atol=1e-9))


def cargar(carpeta):
    carpeta=Path(carpeta)
    faltan=[n for n in ARCHIVOS if not (carpeta/n).is_file()]
    exigir(not faltan,f'Faltan archivos en {carpeta}: {", ".join(faltan)}')
    ev={n:leer_json(carpeta/n) for n in ARCHIVOS if n.endswith('.json')}
    ev.update({n:pd.read_csv(carpeta/n) for n in ARCHIVOS if n.endswith('.csv')})
    return ev


def verificar_resultados(carpeta):
    """Comprueba la evidencia de una corrida y devuelve sus conteos.

    Lanza EvidenciaInvalida con un mensaje concreto ante cualquier incoherencia.
    """
    ev=cargar(carpeta)
    r,man,runs=ev['resumen.json'],ev['manifiesto.json'],ev['repeticiones.csv']
    exigir(man.get('estado')=='completa',f'El manifiesto declara estado {man.get("estado")!r}; solo una corrida completa es evidencia')

    # Número de réplicas: declarado en resumen y manifiesto, y coherente entre ambos.
    rep=r.get('repeticiones')
    exigir(isinstance(rep,int) and not isinstance(rep,bool) and rep>=MINIMO_REPLICAS,
           f'repeticiones={rep!r}; se requieren al menos {MINIMO_REPLICAS} por condición')
    semillas=man.get('semillas_evaluacion',[])
    exigir(len(semillas)==rep and len(set(semillas))==rep,
           f'El manifiesto tiene {len(semillas)} semillas de evaluación y el resumen declara {rep} réplicas')
    declaradas=man.get('configuracion',{}).get('repeticiones',rep)
    exigir(declaradas==rep,f'La configuración del manifiesto declara {declaradas} réplicas y el resumen {rep}')
    exigir(r.get('semilla_demo')==semillas[0],'La semilla de la demo no es la primera semilla de evaluación')

    # Condiciones y políticas completas, sin duplicados y con las mismas semillas.
    escenarios=[e for e,_,_ in ESCENARIOS]
    exigir(set(runs.escenario)==set(escenarios),f'Condiciones encontradas {sorted(set(runs.escenario))}; se esperaban {sorted(escenarios)}')
    exigir(set(runs.politica)==set(POLITICAS),f'Políticas encontradas {sorted(set(runs.politica))}; se esperaban {list(POLITICAS)}')
    corridas=len(escenarios)*len(POLITICAS)*rep
    exigir(len(runs)==corridas,f'{len(runs)} corridas; se esperaban {corridas} ({len(escenarios)} condiciones × {len(POLITICAS)} políticas × {rep})')
    exigir(not runs.duplicated(['escenario','politica','semilla']).any(),'Hay corridas duplicadas')
    for (e,pol),g in runs.groupby(['escenario','politica']):
        exigir(sorted(g.semilla)==sorted(semillas),f'{e}/{pol}: las semillas no coinciden con el manifiesto')
    for etapa in ['semillas_calibracion','semillas_busqueda','semillas_optimizador']:
        exigir(not set(man[etapa])&set(semillas),f'{etapa} comparte semillas con la evaluación')
    factores={e:(d,s) for e,d,s in ESCENARIOS}
    for e,g in runs.groupby('escenario'):
        exigir((g.factor_demanda==factores[e][0]).all() and (g.factor_servicio==factores[e][1]).all(),f'{e}: factores distintos a los del diseño')

    # Restricciones de la dotación propuesta.
    base=r['parametros']['dotacion_base'];opt=r['dotacion_mejorada']
    validar_dotacion(opt,sum(base))
    exigir(sum(base)==sum(opt)==HORAS_NOMINALES,f'Horas-agente base {sum(base)} y propuesta {sum(opt)}; se esperaban {HORAS_NOMINALES}')
    exigir(all(abs(b-o)<=VARIACION_MAXIMA for b,o in zip(base,opt)),f'La propuesta cambia más de ±{VARIACION_MAXIMA} en alguna franja')
    exigir(runs.fecha_referencia.str.startswith('1999-12').all(),'Hay corridas evaluadas fuera de diciembre')
    exigir((runs.llamadas==runs.atendidas+runs.abandonadas).all(),'Alguna corrida no conserva llamadas')

    # Diferencias pareadas: recalculadas y comparadas con el CSV y con resumen.json.
    dif=ev['diferencias_pareadas.csv']
    esperadas=len(escenarios)*len(METRICAS)
    exigir(len(dif)==esperadas and not dif.duplicated(['escenario','metrica']).any(),
           f'{len(dif)} diferencias pareadas; se esperaban {esperadas} sin repetir')
    dif_json={(x['escenario'],x['metrica']):x for x in r['diferencias']}
    exigir(len(dif_json)==len(r['diferencias'])==esperadas,'resumen.json no contiene todas las diferencias pareadas')
    for e,g in runs.groupby('escenario'):
        b=g[g.politica=='base'].set_index('semilla').sort_index()
        o=g[g.politica=='mejorada'].set_index('semilla').sort_index()
        exigir(b.index.equals(o.index),f'{e}: las parejas no usan las mismas semillas')
        exigir(b.llamadas.equals(o.llamadas) and b.fecha_referencia.equals(o.fecha_referencia),f'{e}: las parejas no comparten llamadas')
        for m in METRICAS:
            calc=resumen(o[m]-b[m])
            fila=dif[(dif.escenario==e)&(dif.metrica==m)]
            exigir(len(fila)==1,f'Falta la diferencia {e}/{m}')
            exigir(int(fila.n.iloc[0])==rep==dif_json[e,m]['n'],f'{e}/{m}: n distinto de {rep}')
            for k in CAMPOS_IC:
                exigir(cercano(calc[k],fila[k].iloc[0]) and cercano(calc[k],dif_json[e,m][k]),f'{e}/{m}/{k}: no coincide con las corridas')

    # Medias por condición y política.
    res=ev['resumen.csv'];res_json={(x['escenario'],x['politica'],x['metrica']):x for x in r['resumen']}
    esperadas=len(escenarios)*len(POLITICAS)*len(METRICAS)
    exigir(len(res)==len(res_json)==len(r['resumen'])==esperadas,f'El resumen por política no tiene las {esperadas} filas esperadas')
    for (e,pol),g in runs.groupby(['escenario','politica']):
        for m in METRICAS:
            calc=resumen(g[m]);fila=res[(res.escenario==e)&(res.politica==pol)&(res.metrica==m)]
            exigir(len(fila)==1,f'Falta el resumen {e}/{pol}/{m}')
            for k in CAMPOS_IC:
                exigir(cercano(calc[k],fila[k].iloc[0]) and cercano(calc[k],res_json[e,pol,m][k]),f'{e}/{pol}/{m}/{k}: no coincide con las corridas')

    # Validación frente a la referencia real de diciembre.
    ref=ev['referencia_diaria.csv'];rd=ref[ref.fecha.str.startswith('1999-12')]
    exigir(len(rd)==r['dias_diciembre'],f'La referencia tiene {len(rd)} días de diciembre y el resumen declara {r["dias_diciembre"]}')
    val=ev['validacion.csv'].set_index('metrica');val_json={x['metrica']:x for x in r['validacion']}
    exigir(sorted(val.index)==sorted(val_json)==sorted(METRICAS_VALIDACION),'La validación no contiene las métricas esperadas')
    normal=runs[runs.escenario=='normal']
    for m in METRICAS_VALIDACION:
        obs=rd[m].mean();sb=normal[normal.politica=='base'][m].mean();so=normal[normal.politica=='mejorada'][m].mean()
        for k,v in [('referencia_diciembre',obs),('simulacion_base',sb),('simulacion_mejorada',so),('cambio_absoluto',so-sb)]:
            exigir(cercano(v,val.loc[m,k]) and cercano(v,val_json[m][k]),f'Validación {m}/{k}: no coincide con las corridas')
    vpd=ev['validacion_por_dia.csv']
    exigir(len(vpd)==len(METRICAS_DIARIAS)*r['dias_diciembre'] and vpd.fecha.nunique()==r['dias_diciembre'],'La validación por día está incompleta')
    for metrica,g in vpd.groupby('metrica'):
        exigir(cercano(g.error.abs().mean(),r['mae_diario'][metrica]),f'MAE diario de {metrica} no coincide')

    # La réplica de la demo es la primera corrida normal.
    demo=ev['demo.json']
    exigir(demo.get('semilla')==semillas[0],'demo.json no corresponde a la primera semilla de evaluación')
    for pol in POLITICAS:
        fila=normal[(normal.politica==pol)&(normal.semilla==semillas[0])].iloc[0]
        for m in METRICAS:
            exigir(cercano(demo[pol]['metricas'][m],fila[m]),f'demo.json {pol}/{m} no coincide con repeticiones.csv')

    return dict(repeticiones=rep,corridas=corridas,condiciones=len(escenarios),politicas=len(POLITICAS),
                diferencias=len(dif),semillas=semillas,resumen=r,manifiesto=man)


def verificar_datos(man):
    for nombre,sha in man['hashes_datos'].items():
        exigir(hashlib.sha256((ROOT/'datos'/nombre).read_bytes()).hexdigest()==sha,
               f'El hash de datos/{nombre} no coincide con el manifiesto (¿finales de línea CRLF?)')
    proc=leer_json(ROOT/'datos/procedencia.json')
    datos=pd.read_csv(ROOT/'datos/llamadas_sin_identificadores.csv')
    incluidos=sum(a['registros_incluidos'] for a in proc['archivos']);dias=sum(a['dias'] for a in proc['archivos'])
    exigir(len(datos)==incluidos and datos.fecha.nunique()==dias,'Los datos no coinciden con datos/procedencia.json')
    exigir(not {'customer_id','call_id','server','vru+line'}&set(datos.columns),'Los datos contienen identificadores')
    equipo=leer_json(ROOT/'equipo.json')
    exigir([p['carne'] for p in equipo['integrantes']]==['23427','231977','241452'],'equipo.json no tiene los carnés esperados')


def cifras_clave(r):
    """Cifras que README, guion e informe deben citar igual que los resultados."""
    def f(x):return f'{x:.2f}'.replace('.',',')
    val={x['metrica']:x for x in r['validacion']}
    d={(x['escenario'],x['metrica']):x for x in r['diferencias']}['normal','sla_pct']
    return [f(val['sla_pct']['simulacion_base']),f(val['sla_pct']['simulacion_mejorada']),f(d['media']),
            f(d['ic95_inf']),f(d['ic95_sup']),f(val['espera_media_s']['error_absoluto_base']),f(r['mae_diario']['espera_media_s'])]


def verificar_documentos(info,raiz=ROOT):
    """README, guion y Word deben citar las cifras y el número de réplicas de la evidencia."""
    from docx import Document
    raiz=Path(raiz);rep=info['repeticiones'];cifras=cifras_clave(info['resumen'])
    word=Document(raiz/'output/word/informe_call_center.docx')
    textos={'README.md':(raiz/'README.md').read_text(encoding='utf-8'),
            'docs/GUION.md':(raiz/'docs/GUION.md').read_text(encoding='utf-8'),
            'output/word/informe_call_center.docx':'\n'.join([p.text for p in word.paragraphs]+
                [c.text for t in word.tables for fila in t.rows for c in fila.cells])}
    restos=re.findall(r'\{[^{}]{1,40}\}',textos['output/word/informe_call_center.docx'])
    exigir(not restos,f'El Word contiene variables sin reemplazar: {", ".join(sorted(set(restos)))}')
    for nombre,texto in textos.items():
        faltan=[c for c in cifras if c not in texto]
        exigir(not faltan,f'{nombre} no cita {", ".join(faltan)}; actualizarlo con los resultados')
        exigir(f'{rep} réplicas' in texto or f'{rep} pares' in texto,f'{nombre} no menciona {rep} réplicas')
        # Menciones del número de réplicas de evaluación ("N réplicas por política/condición", "N pares").
        for n in re.findall(r'(\d+) (?:réplicas (?:por (?:política|condición)|finales|del estudio|de cada política)|pares|semillas (?:distintas|independientes))',texto):
            exigir(int(n)==rep,f'{nombre} menciona {n} réplicas de evaluación; los resultados tienen {rep}')
        for n in re.findall(r'(\d+) (?:corridas|comparaciones individuales)',texto):
            exigir(int(n)==info['corridas'],f'{nombre} menciona {n} corridas; los resultados tienen {info["corridas"]}')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resultados',default='resultados',help='carpeta de la corrida; relativa a la raíz del repositorio')
    a=ap.parse_args(argv)
    carpeta=Path(a.resultados) if Path(a.resultados).is_absolute() else ROOT/a.resultados
    entrega=carpeta.resolve()==(ROOT/'resultados').resolve()
    try:
        info=verificar_resultados(carpeta);verificar_datos(info['manifiesto'])
        if entrega:verificar_documentos(info)
    except EvidenciaInvalida as e:
        print(f'ERROR: {e}',file=sys.stderr);return 1
    print(f'OK: {info["corridas"]} corridas, {info["repeticiones"]} réplicas por condición/política, '
          f'{info["diferencias"]} diferencias pareadas recalculadas, semillas separadas, {HORAS_NOMINALES} horas nominales, restricciones, datos y equipo.')
    if entrega:print('README, guion y Word citan las mismas cifras y réplicas que los resultados.')
    else:print(f'Se verificó solo la evidencia de {carpeta}; README, guion y Word corresponden a resultados/.')
    print('La validación numérica no acredita contribuciones, aprobación docente ni publicación en GitHub.')
    return 0


if __name__=='__main__':sys.exit(main())
