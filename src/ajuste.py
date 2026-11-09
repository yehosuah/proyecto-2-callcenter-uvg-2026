"""Ajuste SOLO con noviembre; ninguna decisión usa diciembre."""
import math
import numpy as np


def parametros_desde_datos(df, concurrencia):
    train=df[df.fecha.str.startswith("1999-11")].copy()
    dias=train.fecha.nunique()
    diarias=train.groupby("fecha").size()
    media=float(diarias.mean())
    cv2=max(0.0,(float(diarias.var(ddof=1))-media)/(media*media))
    tasas=(train.groupby(train.llegada_s//3600).size().reindex(range(17),fill_value=0)/dias).tolist()
    mezcla=train.tipo.value_counts(normalize=True).sort_index().to_dict()
    servicio={}
    for tipo,g in train[train.atendida==1].groupby('tipo'):
        x=g.servicio_s.to_numpy(); m=float(x.mean()); v=float(x.var(ddof=0))
        s2=math.log1p(v/(m*m))
        servicio[tipo]=dict(mu=math.log(m)-s2/2,sigma=math.sqrt(s2),media_s=m,sd_s=math.sqrt(v),n=len(x))
    cn=concurrencia[concurrencia.fecha.str.startswith("1999-11")]
    picos=cn.groupby("hora").pico_ocupados.mean().reindex(range(7,24))
    base=np.clip(np.rint(picos.to_numpy()),1,9).astype(int).tolist()
    positivas=train[train.espera_s>0]
    return dict(llegadas_hora=tasas,cv2_demanda_diaria=cv2,mezcla_tipos=mezcla,servicio=servicio,
        paciencia_media_s=float(train.espera_s.sum()/sum(train.atendida==0)),
        fraccion_prioritaria=float((positivas.prioridad_registrada==2).mean()),
        dotacion_base=base,picos_medios_observados=picos.tolist(),dias_ajuste=int(dias),
        n_ajuste=len(train),umbral_s=120.0,disponibilidad=1.0)


def metricas_reales(df):
    filas=[]
    for fecha,g in df.groupby('fecha'):
        serv=g.atendida==1
        filas.append(dict(fecha=fecha,llamadas=len(g),sla_pct=100*float((serv&(g.espera_s<=120)).mean()),
            abandono_pct=100*float((~serv).mean()),espera_media_s=float(g.espera_s.mean()),
            espera_atendidas_s=float(g.loc[serv,'espera_s'].mean()),
            p90_espera_s=float(g.espera_s.quantile(.9))))
    return filas
