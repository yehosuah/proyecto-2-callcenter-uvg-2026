"""Ajustar, optimizar y evaluar con datos y semillas separados."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import time
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from src.modelo import generar_llamadas, generar_replay, simular, validar_dotacion
from src.ajuste import parametros_desde_datos, metricas_reales
from src.optimizacion import optimizar

ROOT=Path(__file__).resolve().parent
METRICAS=['sla_pct','abandono_pct','espera_media_s','espera_atendidas_s','p90_espera_s','llamadas','utilizacion_pct','extra_min']


def guardar_json(nombre,obj):
    (ROOT/'resultados'/nombre).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False))


def resumen(x):
    x=np.asarray(x,dtype=float); n=len(x); media=float(x.mean()); sd=float(x.std(ddof=1)) if n>1 else 0
    semi=float(student_t.ppf(.975,n-1))*sd/np.sqrt(n) if n>1 else 0
    return dict(n=n,media=media,sd=sd,ic95_inf=media-semi,ic95_sup=media+semi)


def ejecutar(repeticiones=60,iteraciones=400):
    if repeticiones<30:raise ValueError('La entrega requiere al menos 30 repeticiones por condición')
    inicio=time.time(); (ROOT/'resultados').mkdir(exist_ok=True)
    df=pd.read_csv(ROOT/'datos/llamadas_sin_identificadores.csv')
    cn=pd.read_csv(ROOT/'datos/concurrencia_observada.csv')
    p=parametros_desde_datos(df,cn)
    base=p['dotacion_base']
    real=pd.DataFrame(metricas_reales(df));real.to_csv(ROOT/'resultados/referencia_diaria.csv',index=False)
    rn=real[real.fecha.str.startswith('1999-11')]
    rd=real[real.fecha.str.startswith('1999-12')]
    dias={f:list(zip(g.llegada_s,g.tipo)) for f,g in df.groupby('fecha')}
    dias_train={k:v for k,v in dias.items() if k.startswith('1999-11')}
    dias_test={k:v for k,v in dias.items() if k.startswith('1999-12')}
    # Calibración de UN factor de disponibilidad efectiva sobre noviembre.
    semillas_cal=list(range(10000,10030))
    entradas_cal=[generar_replay(dias_train,p,s)[1] for s in semillas_cal]
    cal=[]
    for disp in np.round(np.arange(.60,1.001,.025),3):
        mm=[simular(e,base,float(disp))['metricas'] for e in entradas_cal]
        # Escalas fijadas antes de evaluar: 10 s, 5 pp y 5 pp.
        med={m:float(np.mean([r[m] for r in mm])) for m in ['espera_media_s','abandono_pct','sla_pct']}
        perdida=sum(((med[m]-float(rn[m].mean()))/escala)**2 for m,escala in
                    [('espera_media_s',10),('abandono_pct',5),('sla_pct',5)])
        cal.append(dict(disponibilidad=float(disp),perdida=perdida,**med))
    p['disponibilidad']=min(cal,key=lambda r:r['perdida'])['disponibilidad']
    pd.DataFrame(cal).to_csv(ROOT/'resultados/calibracion.csv',index=False)
    print('CALIBRACION',p['disponibilidad'],'BASE',base,'HORAS',sum(base),flush=True)
    guardar_json('parametros.json',p)
    # Entradas de búsqueda: ocho días sintéticos NHPP con variación diaria,
    # ajustados exclusivamente con noviembre. Semillas distintas de calibración/evaluación.
    semillas_busqueda=list(range(30000,30008))
    entradas_busqueda=[generar_llamadas(p,s) for s in semillas_busqueda]
    candidatas=[]
    for semilla in [7301,7302,7303]:
        r=optimizar(base,entradas_busqueda,p['disponibilidad'],semilla,iteraciones)
        pd.DataFrame(r.pop('traza')).to_csv(ROOT/f'resultados/busqueda_{semilla}.csv',index=False)
        candidatas.append(r)
        print('BUSQUEDA',semilla,'COSTO',r['costo'],'DOTACION',r['dotacion'],flush=True)
    opt=min(candidatas,key=lambda r:r['costo'])['dotacion']
    validar_dotacion(opt,sum(base))
    guardar_json('optimizacion.json',dict(candidatas=candidatas,seleccionada=opt,
        temperatura_inicial=2.0,temperatura_final=.02,semillas_busqueda=semillas_busqueda,
        criterio='minimizar porcentaje de solicitudes no atendidas antes de 120 s'))
    pd.DataFrame(dict(hora=range(7,24),base=base,mejorada=opt,llegadas_hora_noviembre=p['llegadas_hora']))\
        .to_csv(ROOT/'resultados/dotacion.csv',index=False)
    filas=[]; demos={}
    escenarios=[('demanda_80',.8,1.0),('normal',1.,1.),('demanda_120',1.2,1.),
                ('demanda_140',1.4,1.),('servicio_115',1.,1.15)]
    semillas_test=list(range(100000,100000+repeticiones))
    for escenario,demanda,servicio in escenarios:
        for seed in semillas_test:
            fecha,entradas=generar_replay(dias_test,p,seed,demanda,servicio)
            for politica,c in [('base',base),('mejorada',opt)]:
                trace=(escenario=='normal' and seed==semillas_test[0])
                r=simular(entradas,c,p['disponibilidad'],traza=trace)
                filas.append(dict(escenario=escenario,politica=politica,semilla=seed,fecha_referencia=fecha,
                    factor_demanda=demanda,factor_servicio=servicio,**r['metricas']))
                if trace:demos[politica]=r
        print('EVALUADO',escenario,repeticiones,'replicas por politica',flush=True)
    resultados=pd.DataFrame(filas);resultados.to_csv(ROOT/'resultados/repeticiones.csv',index=False)
    tab=[]
    for (e,pol),g in resultados.groupby(['escenario','politica']):
        for m in METRICAS:tab.append(dict(escenario=e,politica=pol,metrica=m,**resumen(g[m])))
    res=pd.DataFrame(tab);res.to_csv(ROOT/'resultados/resumen.csv',index=False)
    dif=[]
    for e,g in resultados.groupby('escenario'):
        b=g[g.politica=='base'].set_index('semilla');o=g[g.politica=='mejorada'].set_index('semilla')
        for m in METRICAS:
            dif.append(dict(escenario=e,metrica=m,**resumen(o[m]-b[m]),
                cambio_relativo_pct=100*(float(o[m].mean())-float(b[m].mean()))/float(b[m].mean())
                if float(b[m].mean()) else 0.0))
    pd.DataFrame(dif).to_csv(ROOT/'resultados/diferencias_pareadas.csv',index=False)
    valid=[]
    for m in ['llamadas','sla_pct','abandono_pct','espera_media_s','espera_atendidas_s','p90_espera_s']:
        b=resultados[(resultados.escenario=='normal')&(resultados.politica=='base')]
        o=resultados[(resultados.escenario=='normal')&(resultados.politica=='mejorada')]
        obs=float(rd[m].mean());sb=float(b[m].mean());so=float(o[m].mean())
        valid.append(dict(metrica=m,referencia_diciembre=obs,simulacion_base=sb,simulacion_mejorada=so,
            error_absoluto_base=abs(sb-obs),error_relativo_base_pct=100*abs(sb-obs)/abs(obs),
            cambio_absoluto=so-sb,cambio_relativo_pct=100*(so-sb)/sb))
    pd.DataFrame(valid).to_csv(ROOT/'resultados/validacion.csv',index=False)
    # Validación por día empareja realmente el mismo patrón de llegadas.
    vd=[]
    for i,(fecha,entradas_dia) in enumerate(sorted(dias_test.items())):
        mm=[simular(generar_replay({fecha:entradas_dia},p,200000+i*30+j)[1],base,p['disponibilidad'])['metricas'] for j in range(30)]
        obs=rd.set_index('fecha').loc[fecha]
        for m in ['sla_pct','abandono_pct','espera_media_s']:
            pred=float(np.mean([r[m] for r in mm]));vd.append(dict(fecha=fecha,metrica=m,real=float(obs[m]),predicho=pred,error=pred-float(obs[m])))
    vdf=pd.DataFrame(vd);vdf.to_csv(ROOT/'resultados/validacion_por_dia.csv',index=False)
    mae={m:float(g.error.abs().mean()) for m,g in vdf.groupby('metrica')}
    guardar_json('demo.json',dict(semilla=semillas_test[0],parametros=p,dotacion_base=base,dotacion_mejorada=opt,**demos))
    guardar_json('resumen.json',dict(parametros=p,dotacion_mejorada=opt,validacion=valid,mae_diario=mae,
        diferencias=dif,resumen=tab,repeticiones=repeticiones,fuente_datos='Technion, noviembre/diciembre 1999',
        n_diciembre=int(sum(df.fecha.str.startswith('1999-12'))),dias_diciembre=len(rd),
        semilla_demo=semillas_test[0]))
    manifiesto=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
        semillas_calibracion=semillas_cal,semillas_busqueda=semillas_busqueda,semillas_optimizador=[7301,7302,7303],
        semillas_evaluacion=semillas_test,semillas_validacion_diaria='200000 + 30 * indice_dia + repeticion (0..29)',
        iteraciones=iteraciones,segundos_ejecucion=round(time.time()-inicio,2),
        definicion_ic='Student t 95% entre réplicas; diferencias pareadas. Condicional a parámetros y distribución empírica de días de diciembre.',
        hashes_datos={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'datos').glob('*.csv'))})
    guardar_json('manifiesto.json',manifiesto)
    print(pd.DataFrame(valid).to_string(index=False),flush=True)
    print('MAE DIARIO',mae,'SEGUNDOS',manifiesto['segundos_ejecucion'],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repeticiones',type=int,default=60);ap.add_argument('--iteraciones',type=int,default=400)
    a=ap.parse_args();ejecutar(a.repeticiones,a.iteraciones)
