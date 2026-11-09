"""Demo local: ejecuta el mismo motor que generó los experimentos."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json
import math
import pandas as pd
from src.modelo import simular,generar_llamadas,generar_replay

ROOT=Path(__file__).resolve().parent


def leer(nombre):return json.loads((ROOT/'resultados'/nombre).read_text())


def comparar(entrada):
    if not isinstance(entrada,dict):raise ValueError('Se requiere un objeto JSON')
    semilla=entrada.get('semilla',100000)
    if isinstance(semilla,bool) or not isinstance(semilla,(int,float)) or not math.isfinite(semilla) or int(semilla)!=semilla:
        raise ValueError('La semilla debe ser un entero')
    seed=int(semilla);dem=float(entrada.get('demanda',1));ser=float(entrada.get('servicio',1))
    if not 0<=seed<2**32 or not .25<=dem<=2 or not .5<=ser<=2:
        raise ValueError('Semilla o factores fuera de rango')
    r=leer('resumen.json');p=r['parametros']
    fuente=entrada.get('fuente','diciembre')
    if fuente=='diciembre':
        df=pd.read_csv(ROOT/'datos/llamadas_sin_identificadores.csv');df=df[df.fecha.str.startswith('1999-12')]
        dias={f:list(zip(g.llegada_s,g.tipo)) for f,g in df.groupby('fecha')}
        fecha,llamadas=generar_replay(dias,p,seed,dem,ser)
    elif fuente=='nhpp':fecha='Día sintético';llamadas=generar_llamadas(p,seed,dem,ser)
    else:raise ValueError('Fuente no admitida')
    out=dict(semilla=seed,fecha=fecha,fuente=fuente,demanda=dem,servicio=ser)
    for pol,c in [('base',p['dotacion_base']),('mejorada',r['dotacion_mejorada'])]:
        s=simular(llamadas,c,p['disponibilidad'],traza=True)
        # Conserva eventos de cola y ocupación para un gráfico escalonado exacto.
        out[pol]={'metricas':s['metricas'],'traza':s['traza'],'dotacion':c}
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def enviar(self,codigo,contenido,tipo='application/json; charset=utf-8'):
        b=contenido if isinstance(contenido,bytes) else json.dumps(contenido,allow_nan=False).encode()
        self.send_response(codigo);self.send_header('Content-Type',tipo);self.send_header('Content-Length',str(len(b)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':self.enviar(200,(ROOT/'web/index.html').read_bytes(),'text/html; charset=utf-8')
        elif path=='/api/evidencia':self.enviar(200,leer('resumen.json'))
        elif path=='/favicon.ico':self.enviar(204,b'','image/x-icon')
        else:self.enviar(404,{'error':'Recurso no encontrado'})
    def do_POST(self):
        if self.path!='/api/simular':return self.enviar(404,{'error':'Recurso no encontrado'})
        try:
            largo=int(self.headers.get('Content-Length','0'))
            if not 0<largo<=4096:raise ValueError('Cuerpo inválido')
            entrada=json.loads(self.rfile.read(largo));self.enviar(200,comparar(entrada))
        except (ValueError,TypeError,KeyError,OverflowError) as e:self.enviar(400,{'error':str(e)})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);a=ap.parse_args()
    print(f'Demo del call-center: http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
