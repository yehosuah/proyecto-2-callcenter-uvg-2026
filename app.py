"""Demo local: ejecuta el mismo motor que generó los experimentos.

Respuestas de la API (siempre JSON con la clave "error" cuando algo falla):
    200  simulación o evidencia correctas
    400  solicitud inválida: JSON mal formado o parámetros fuera de rango
    404  ruta desconocida
    405  método no admitido en una ruta existente
    413  cuerpo demasiado grande
    500  falla del servidor: evidencia o datos ausentes o dañados, error interno
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json
import math
import socket
import sys
import traceback
import pandas as pd
from src.modelo import simular,generar_llamadas,generar_replay

ROOT=Path(__file__).resolve().parent
# Rutas configurables (--resultados) y sustituibles en pruebas sin tocar los archivos reales.
RESULTADOS=ROOT/'resultados'
DATOS=ROOT/'datos/llamadas_sin_identificadores.csv'
PAGINA=ROOT/'web/index.html'
MAX_CUERPO=4096
FUENTES=('diciembre','nhpp')


class EntradaInvalida(ValueError):
    """Error del usuario: se responde 400."""


class CuerpoDemasiadoGrande(ValueError):
    """Se responde 413."""


class EvidenciaNoDisponible(RuntimeError):
    """Resultados o datos ausentes o dañados: falla del servidor, se responde 500."""


def numero(entrada,clave,defecto):
    x=entrada.get(clave,defecto)
    if isinstance(x,bool) or not isinstance(x,(int,float)):
        raise EntradaInvalida(f'"{clave}" debe ser un número')
    try:x=float(x)
    except OverflowError:raise EntradaInvalida(f'"{clave}" está fuera de rango') from None
    if not math.isfinite(x):raise EntradaInvalida(f'"{clave}" debe ser un número finito')
    return x


def validar_entrada(entrada):
    """Valida solo lo que envía el usuario; no lee archivos."""
    if not isinstance(entrada,dict):raise EntradaInvalida('Se requiere un objeto JSON')
    semilla=numero(entrada,'semilla',100000)
    if int(semilla)!=semilla:raise EntradaInvalida('La semilla debe ser un entero')
    seed=int(semilla);dem=numero(entrada,'demanda',1);ser=numero(entrada,'servicio',1)
    if not 0<=seed<2**32:raise EntradaInvalida('La semilla debe estar entre 0 y 4294967295')
    if not .25<=dem<=2:raise EntradaInvalida('La demanda debe estar entre 0,25 y 2')
    if not .5<=ser<=2:raise EntradaInvalida('La duración de servicio debe estar entre 0,5 y 2')
    fuente=entrada.get('fuente','diciembre')
    if fuente not in FUENTES:raise EntradaInvalida(f'Fuente no admitida; usar {" o ".join(FUENTES)}')
    return seed,dem,ser,fuente


def cargar_resumen():
    """Lee resultados/resumen.json y comprueba las claves que usan la API y la interfaz."""
    ruta=RESULTADOS/'resumen.json'
    try:r=json.loads(ruta.read_text(encoding='utf-8'))
    except FileNotFoundError:raise EvidenciaNoDisponible(f'No se encontró la evidencia {ruta.name} en {RESULTADOS.name}/') from None
    except (OSError,ValueError) as e:raise EvidenciaNoDisponible(f'La evidencia {ruta.name} está dañada: {e}') from None
    if not isinstance(r,dict):raise EvidenciaNoDisponible(f'La evidencia {ruta.name} no es un objeto JSON')
    p=r.get('parametros') if isinstance(r.get('parametros'),dict) else {}
    faltan=[k for k in ['parametros','dotacion_mejorada','repeticiones','dias_diciembre','validacion','mae_diario','diferencias'] if k not in r]
    faltan+=[f'parametros.{k}' for k in ['dotacion_base','disponibilidad'] if k not in p]
    if faltan:raise EvidenciaNoDisponible(f'La evidencia {ruta.name} está incompleta; faltan: {", ".join(faltan)}')
    return r


def cargar_dias_diciembre():
    try:
        df=pd.read_csv(DATOS);df=df[df.fecha.str.startswith('1999-12')]
        dias={f:list(zip(g.llegada_s,g.tipo)) for f,g in df.groupby('fecha')}
    except FileNotFoundError:raise EvidenciaNoDisponible(f'No se encontraron los datos {DATOS.name}') from None
    except Exception as e:raise EvidenciaNoDisponible(f'Los datos {DATOS.name} están dañados: {e}') from None
    if not dias:raise EvidenciaNoDisponible(f'Los datos {DATOS.name} no contienen días de diciembre')
    return dias


def comparar(entrada):
    seed,dem,ser,fuente=validar_entrada(entrada)
    r=cargar_resumen();p=r['parametros']
    if fuente=='diciembre':fecha,llamadas=generar_replay(cargar_dias_diciembre(),p,seed,dem,ser)
    else:fecha='Día sintético';llamadas=generar_llamadas(p,seed,dem,ser)
    out=dict(semilla=seed,fecha=fecha,fuente=fuente,demanda=dem,servicio=ser)
    for pol,c in [('base',p['dotacion_base']),('mejorada',r['dotacion_mejorada'])]:
        s=simular(llamadas,c,p['disponibilidad'],traza=True)
        # Conserva eventos de cola y ocupación para un gráfico escalonado exacto.
        out[pol]={'metricas':s['metricas'],'traza':s['traza'],'dotacion':c}
    return out


class Handler(BaseHTTPRequestHandler):
    RUTAS={'/':'GET','/api/evidencia':'GET','/favicon.ico':'GET','/api/simular':'POST'}

    def log_message(self,*args):pass

    def enviar(self,codigo,contenido,tipo='application/json; charset=utf-8',extra=None):
        b=contenido if isinstance(contenido,bytes) else json.dumps(contenido,allow_nan=False,ensure_ascii=False).encode('utf-8')
        self.send_response(codigo);self.send_header('Content-Type',tipo);self.send_header('Content-Length',str(len(b)))
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.send_header('Cache-Control','no-store');self.end_headers()
        if self.command!='HEAD':self.wfile.write(b)

    def atender(self,metodo):
        """Toda solicitud recibe una respuesta; nunca se cierra la conexión sin contestar."""
        ruta=urlparse(self.path).path
        if ruta not in self.RUTAS:return self.enviar(404,{'error':'Recurso no encontrado'})
        if self.RUTAS[ruta]!=metodo:
            return self.enviar(405,{'error':f'Método no admitido; usar {self.RUTAS[ruta]}'},extra={'Allow':self.RUTAS[ruta]})
        try:
            if ruta=='/':
                try:pagina=PAGINA.read_bytes()
                except OSError:raise EvidenciaNoDisponible('No se encontró la interfaz web/index.html') from None
                self.enviar(200,pagina,'text/html; charset=utf-8')
            elif ruta=='/favicon.ico':self.enviar(204,b'','image/x-icon')
            elif ruta=='/api/evidencia':self.enviar(200,cargar_resumen())
            else:self.enviar(200,comparar(self.leer_json()))
        except EntradaInvalida as e:self.enviar(400,{'error':str(e)})
        except CuerpoDemasiadoGrande as e:self.enviar(413,{'error':str(e)})
        except EvidenciaNoDisponible as e:self.enviar(500,{'error':str(e)})
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.enviar(500,{'error':'Error interno del servidor; revisar la consola donde corre app.py'})

    def leer_json(self):
        try:largo=int(self.headers.get('Content-Length',''))
        except ValueError:raise EntradaInvalida('Falta Content-Length o no es un entero') from None
        if largo>MAX_CUERPO:raise CuerpoDemasiadoGrande(f'El cuerpo supera {MAX_CUERPO} bytes')
        if largo<=0:raise EntradaInvalida('El cuerpo está vacío; enviar un objeto JSON')
        try:return json.loads(self.rfile.read(largo).decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError):raise EntradaInvalida('El cuerpo no es JSON válido') from None

    def do_GET(self):self.atender('GET')
    def do_HEAD(self):self.atender('GET')
    def do_POST(self):self.atender('POST')
    def do_PUT(self):self.atender('PUT')
    def do_DELETE(self):self.atender('DELETE')
    def do_PATCH(self):self.atender('PATCH')


class Servidor(ThreadingHTTPServer):
    """En Windows, SO_REUSEADDR deja arrancar una segunda demo en un puerto ocupado sin
    recibir tráfico: el navegador seguiría hablando con la demo anterior. Se reserva el
    puerto en exclusiva para que el conflicto se detecte al iniciar."""
    allow_reuse_address=sys.platform!='win32'

    def server_bind(self):
        if sys.platform=='win32' and hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


def main(argv=None):
    global RESULTADOS
    ap=argparse.ArgumentParser(description='Demo local del call-center')
    ap.add_argument('--port',type=int,default=8765)
    ap.add_argument('--resultados',default='resultados',help='carpeta de la corrida; relativa a la raíz del repositorio')
    a=ap.parse_args(argv)
    RESULTADOS=Path(a.resultados) if Path(a.resultados).is_absolute() else ROOT/a.resultados
    try:servidor=Servidor(('127.0.0.1',a.port),Handler)
    except OSError:
        print(f'El puerto {a.port} está ocupado (¿otra demo abierta?). Cerrarla con Ctrl+C o usar: python app.py --port {a.port+1}',file=sys.stderr)
        return 1
    print(f'Demo del call-center: http://127.0.0.1:{a.port}  (evidencia: {RESULTADOS})',flush=True)
    try:servidor.serve_forever()
    except KeyboardInterrupt:pass
    finally:servidor.server_close()
    return 0


if __name__=='__main__':sys.exit(main())
