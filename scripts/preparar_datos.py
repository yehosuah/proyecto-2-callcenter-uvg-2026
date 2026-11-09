"""Descarga verificable y eliminación de identificadores personales antes de guardar."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from urllib.request import urlopen
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = "https://serveng.technion.ac.il/files/Homeworks/callcenterdata/"
ARCHIVOS = {"NovemberTxt.ZIP": "8b14fdc9e0d0bbead85575069aeea75991b9839a0ac2601f3f5b0b6b77b5094b",
            "DecemberTxt.ZIP": "3e3eb51e10cf1b9dd44c15d70c0a6e88b029a7420f91f9882a471f1f3558951b"}


def segundos(s):
    return s.str.split(":", expand=True).astype(int).mul([3600,60,1]).sum(axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    (ROOT/"datos").mkdir(exist_ok=True)
    todos, auditoria, concurrencia = [], [], []
    for nombre, esperado in ARCHIVOS.items():
        contenido = (args.cache/nombre).read_bytes() if args.cache else urlopen(URL+nombre, timeout=60).read()
        sha = hashlib.sha256(contenido).hexdigest()
        if sha != esperado:
            raise ValueError(f"Cambió la fuente {nombre}: revisar antes de continuar")
        z = zipfile.ZipFile(io.BytesIO(contenido))
        df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep=r"\s+")
        original = len(df)
        pasos=[]
        def filtrar(mascara, motivo):
            nonlocal df
            antes=len(df); df=df[mascara].copy(); pasos.append({"criterio":motivo,"excluidos":antes-len(df),"restantes":len(df)})
        df["fecha"] = pd.to_datetime(df.date.astype(str), format="%y%m%d")
        filtrar(df.fecha.dt.dayofweek.isin([6,0,1,2,3]), "Días laborales locales: domingo a jueves")
        filtrar(df.type.isin(["PS","NE","NW"]), "Servicios PS, NE y NW; se excluyen IN, PE y TT")
        filtrar(df.outcome.isin(["AGENT","HANG"]), "Se excluyen llamadas PHANTOM")
        filtrar((df.outcome=="AGENT") | (df.q_start!="00:00:00"), "Solo solicitudes de agente; se excluye abandono en VRU")
        df["llegada_s"] = segundos(df.vru_exit)
        filtrar((df.llegada_s>=25200)&(df.llegada_s<86400), "Entrada a cola entre 07:00 y 24:00")
        filtrar((df.q_time>=0)&((df.outcome!="AGENT")|(df.ser_time>0)), "Duraciones válidas")
        df["inicio_s"] = segundos(df.ser_start)
        df.loc[(df.outcome=="AGENT")&(df.inicio_s < df.llegada_s-60),"inicio_s"] += 86400
        for fecha,g in df[df.outcome=="AGENT"].groupby("fecha"):
            eventos=[]
            for a,d in zip(g.inicio_s,g.ser_time):eventos.extend([(int(a),1),(int(a+d),-1)])
            eventos.sort(key=lambda v:(v[0],v[1]))
            for hora in range(7,24):
                busy=sum(d for t,d in eventos if t<hora*3600); pico=busy
                for t,d in eventos:
                    if hora*3600 <= t < (hora+1)*3600:busy+=d;pico=max(pico,busy)
                concurrencia.append(dict(fecha=fecha.strftime('%Y-%m-%d'),hora=hora,pico_ocupados=pico))
        seguro=pd.DataFrame(dict(fecha=df.fecha.dt.strftime('%Y-%m-%d'),tipo=df.type,
            llegada_s=df.llegada_s-25200,espera_s=df.q_time,servicio_s=df.ser_time,
            atendida=(df.outcome=="AGENT").astype(int),prioridad_registrada=df.priority))
        todos.append(seguro)
        auditoria.append(dict(archivo=nombre,url=URL+nombre,sha256=sha,registros_originales=original,
            registros_incluidos=len(seguro),dias=int(seguro.fecha.nunique()),filtros=pasos))
    datos=pd.concat(todos).sort_values(["fecha","llegada_s","tipo"]).reset_index(drop=True)
    datos.to_csv(ROOT/"datos/llamadas_sin_identificadores.csv",index=False)
    pd.DataFrame(concurrencia).to_csv(ROOT/"datos/concurrencia_observada.csv",index=False)
    (ROOT/"datos/procedencia.json").write_text(json.dumps(dict(
        fuente="Ilan Guedj y Avi Mandelbaum, Technion; Anonymous Bank, 1999",
        documentacion=URL+"documentation.pdf",archivos=auditoria,
        privacidad="Se eliminaron customer_id, call_id, vru+line y server; no se guardan archivos brutos.",
        uso="La documentación permite uso gratuito, pide atribución y notificar a Avi Mandelbaum. No se ha enviado una notificación desde este proyecto."),indent=2,ensure_ascii=False))
    print(json.dumps({"incluidos":len(datos),"auditoria":auditoria},indent=2,ensure_ascii=False))


if __name__=="__main__":main()
