"""Figuras científicas reproducibles a partir de tablas guardadas."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parent
VERDE='#ff7f0e';AZUL='#1f77b4';ROJO='#d62728';GRIS='#7f7f7f'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
 'font.size':12,'axes.spines.top':False,'axes.spines.right':False,
 'axes.titleweight':'normal','axes.labelcolor':'black','text.color':'black',
 'axes.titlesize':12,'savefig.dpi':180})


def guardar(fig,nombre):
    fig.tight_layout();fig.savefig(R/f'figuras/{nombre}.png',facecolor='white',bbox_inches='tight')
    fig.savefig(R/f'figuras/{nombre}.pdf',facecolor='white',bbox_inches='tight');plt.close(fig)


def main():
    (R/'figuras').mkdir(exist_ok=True)
    resumen=json.loads((R/'resultados/resumen.json').read_text())
    dot=pd.read_csv(R/'resultados/dotacion.csv');rr=pd.read_csv(R/'resultados/resumen.csv')
    df=pd.read_csv(R/'datos/llamadas_sin_identificadores.csv')
    fig,axs=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for mes,color,label in [('1999-11',AZUL,'Noviembre: ajuste'),('1999-12',VERDE,'Diciembre: referencia')]:
        d=df[df.fecha.str.startswith(mes)];y=d.groupby(d.llegada_s//3600).size()/d.fecha.nunique()
        axs[0].plot(np.arange(7,24),y.values,'o-',color=color,label=label,ms=4)
    axs[0].set_title('Demanda observada y distribución de capacidad');axs[0].set_ylabel('Solicitudes por hora');axs[0].legend(frameon=False)
    axs[1].step(dot.hora,dot.base,where='mid',label='Base inferida',color=AZUL,lw=2)
    axs[1].step(dot.hora,dot.mejorada,where='mid',label='Propuesta',color=VERDE,lw=2)
    axs[1].set(xlabel='Hora local del call-center',ylabel='Agentes disponibles',xticks=range(7,24),ylim=(0,10));axs[1].legend(frameon=False)
    guardar(fig,'01_demanda_y_capacidad')
    fig,axs=plt.subplots(1,3,figsize=(11,3.6))
    valid=pd.read_csv(R/'resultados/validacion.csv').set_index('metrica')
    for ax,m,titulo,unidad in zip(axs,['sla_pct','abandono_pct','espera_media_s'],['Atendidas en ≤ 120 s','Abandono','Espera de todas las solicitudes'],['%','%','segundos']):
        v=valid.loc[m];vals=[v.referencia_diciembre,v.simulacion_base,v.simulacion_mejorada]
        ax.bar(['Real','Base','Propuesta'],vals,color=[GRIS,AZUL,VERDE],width=.6)
        for i,x in enumerate(vals):ax.text(i,x+max(vals)*.035,f'{x:.2f}',ha='center',fontsize=10)
        ax.set(ylabel=unidad,title=titulo,ylim=(0,max(vals)*1.2))
    guardar(fig,'02_comparacion_real')
    dd=pd.read_csv(R/'resultados/diferencias_pareadas.csv')
    n=dd[dd.escenario=='normal'].set_index('metrica')
    fig,axs=plt.subplots(1,3,figsize=(11,3.3))
    for ax,m,label in zip(axs,['sla_pct','abandono_pct','espera_media_s'],['Δ atención ≤ 120 s (pp)','Δ abandono (pp)','Δ espera total (s)']):
        r=n.loc[m];ax.errorbar([r.media],[0],xerr=[[r.media-r.ic95_inf],[r.ic95_sup-r.media]],fmt='o',color=VERDE,ms=8,capsize=6)
        ax.axvline(0,color=GRIS,lw=1,ls='--');ax.set(yticks=[],xlabel=label,title=f'{r.media:+.2f} [{r.ic95_inf:+.2f}, {r.ic95_sup:+.2f}]')
    fig.suptitle('Diferencia propuesta menos base · IC 95% pareado',fontsize=13,y=1.04)
    guardar(fig,'03_incertidumbre')
    fig,axs=plt.subplots(1,2,figsize=(10,3.7))
    for pol,color,label in [('base',AZUL,'Base'),('mejorada',VERDE,'Propuesta')]:
        for ax,m,yl in zip(axs,['sla_pct','abandono_pct'],['Atendidas en ≤ 120 s (%)','Abandono (%)']):
            rows=[rr[(rr.escenario==e)&(rr.politica==pol)&(rr.metrica==m)].iloc[0] for e in ['demanda_80','normal','demanda_120','demanda_140']]
            ax.errorbar([.8,1,1.2,1.4],[r.media for r in rows],yerr=[(r.ic95_sup-r.ic95_inf)/2 for r in rows],color=color,marker='o',capsize=4,label=label)
            ax.set(xlabel='Factor de demanda respecto de diciembre',ylabel=yl,xticks=[.8,1,1.2,1.4]);ax.legend(frameon=False)
    fig.suptitle('Sensibilidad de la propuesta fija a la demanda',fontsize=13,y=1.04)
    guardar(fig,'04_sensibilidad')
    vd=pd.read_csv(R/'resultados/validacion_por_dia.csv')
    fig,axs=plt.subplots(1,2,figsize=(10,3.7))
    for ax,m,label in zip(axs,['espera_media_s','sla_pct'],['Espera media (s)','Atendidas en ≤ 120 s (%)']):
        g=vd[vd.metrica==m];lim=max(g.real.max(),g.predicho.max())*1.05
        ax.scatter(g.real,g.predicho,color=VERDE,alpha=.8,s=35);ax.plot([0,lim],[0,lim],ls='--',color=GRIS)
        ax.set(xlabel=f'Referencia real · {label}',ylabel=f'Simulación base · {label}',title=f'MAE diario = {g.error.abs().mean():.2f}',xlim=(0,lim),ylim=(0,lim))
    fig.suptitle('Validación por día de diciembre · 30 simulaciones por día',fontsize=13,y=1.04)
    guardar(fig,'05_validacion_diaria')
    fig,ax=plt.subplots(figsize=(9,3.6))
    for seed,color in zip([7301,7302,7303],[AZUL,GRIS,VERDE]):
        g=pd.read_csv(R/f'resultados/busqueda_{seed}.csv');ax.plot(g.iteracion,g.mejor_costo,label=f'Semilla {seed}',color=color)
    ax.set(xlabel='Iteración',ylabel='Solicitudes fuera de 120 s (%)',title='Recocido simulado: mejor objetivo encontrado');ax.legend(frameon=False)
    guardar(fig,'06_busqueda')
    demo=json.loads((R/'resultados/demo.json').read_text());fig,axs=plt.subplots(2,1,figsize=(10,5.5),sharex=True)
    for pol,color,label in [('base',AZUL,'Base'),('mejorada',VERDE,'Propuesta')]:
        t=np.array(demo[pol]['traza']);axs[0].step(t[:,0]/3600+7,t[:,1],where='post',color=color,lw=.9,label=label)
        axs[1].step(t[:,0]/3600+7,t[:,2],where='post',color=color,lw=.9,label=label)
    axs[0].set(ylabel='Solicitudes en cola',title=f'Una réplica del sistema · semilla {demo["semilla"]}');axs[0].legend(frameon=False)
    axs[1].set(xlabel='Hora local',ylabel='Agentes ocupados',xlim=(7,24),xticks=range(7,25))
    guardar(fig,'07_trayectoria')
    print('7 figuras exportadas en PNG y PDF')


if __name__=='__main__':main()
