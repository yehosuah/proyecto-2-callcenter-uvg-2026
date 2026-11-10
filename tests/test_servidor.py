"""D2: rutas HTTP de la demo con un servidor temporal.

La evidencia ausente o dañada se simula con carpetas temporales; nunca se tocan
resultados/ ni datos/ reales.
"""
import contextlib
import http.client
import io
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from http.server import ThreadingHTTPServer
import app

ROOT=Path(__file__).resolve().parents[1]


class ServidorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.hilo=threading.Thread(target=cls.srv.serve_forever,daemon=True);cls.hilo.start()
        cls.demo=json.loads((ROOT/'resultados/demo.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown();cls.srv.server_close();cls.hilo.join(5)

    def setUp(self):
        self._tmp=tempfile.TemporaryDirectory();self.tmp=Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def pedir(self,metodo,ruta,cuerpo=None,cabeceras=None):
        c=http.client.HTTPConnection('127.0.0.1',self.srv.server_port,timeout=60)
        try:
            if isinstance(cuerpo,(dict,list)):cuerpo=json.dumps(cuerpo)
            if isinstance(cuerpo,str):cuerpo=cuerpo.encode('utf-8')
            c.request(metodo,ruta,body=cuerpo,headers={'Content-Type':'application/json',**(cabeceras or {})})
            r=c.getresponse();datos=r.read()
            return r.status,r.getheader('Content-Type',''),datos
        finally:c.close()

    def pedir_json(self,*args,**kw):
        codigo,tipo,datos=self.pedir(*args,**kw)
        self.assertTrue(tipo.startswith('application/json'),f'{codigo} sin JSON: {tipo}')
        return codigo,json.loads(datos.decode('utf-8'))

    def evidencia_temporal(self,contenido=None,quitar=()):
        """Carpeta temporal con resumen.json real, reemplazado o recortado."""
        carpeta=self.tmp/'resultados';carpeta.mkdir()
        if contenido is None:
            r=json.loads((ROOT/'resultados/resumen.json').read_text(encoding='utf-8'))
            for k in quitar:r.pop(k)
            contenido=json.dumps(r)
        if contenido is not False:(carpeta/'resumen.json').write_text(contenido,encoding='utf-8')
        return mock.patch.object(app,'RESULTADOS',carpeta)

    # Casos correctos
    def test_pagina_principal(self):
        codigo,tipo,datos=self.pedir('GET','/')
        self.assertEqual(codigo,200);self.assertTrue(tipo.startswith('text/html'))
        self.assertIn('<title>',datos.decode('utf-8'))

    def test_evidencia(self):
        codigo,r=self.pedir_json('GET','/api/evidencia')
        self.assertEqual(codigo,200);self.assertEqual(r['repeticiones'],60)

    def test_simulacion_valida_reproduce_demo(self):
        codigo,r=self.pedir_json('POST','/api/simular',{'semilla':100000})
        self.assertEqual(codigo,200)
        for pol in ['base','mejorada']:self.assertEqual(r[pol]['metricas'],self.demo[pol]['metricas'])
        self.assertEqual((r['semilla'],r['demanda'],r['servicio'],r['fuente']),(100000,1.0,1.0,'diciembre'))

    def test_simulacion_sintetica(self):
        codigo,r=self.pedir_json('POST','/api/simular',{'semilla':7,'fuente':'nhpp','demanda':1.4})
        self.assertEqual(codigo,200);self.assertEqual(r['fecha'],'Día sintético')

    # Errores del usuario: 400
    def test_solicitudes_invalidas_devuelven_400(self):
        casos={'JSON mal formado':'{malo','no es objeto':[1,2],'texto':'"hola"','semilla decimal':{'semilla':1.5},
               'semilla negativa':{'semilla':-1},'semilla booleana':{'semilla':True},'semilla gigante':{'semilla':2**40},
               'demanda texto':{'demanda':'x'},'demanda nula':{'demanda':None},'demanda NaN':'{"demanda": NaN}',
               'demanda infinita':'{"demanda": Infinity}','demanda fuera de rango':{'demanda':3},
               'servicio fuera de rango':{'servicio':.1},'fuente desconocida':{'fuente':'otra'},
               'bytes no UTF-8':b'\xff\xfe{'}
        for nombre,cuerpo in casos.items():
            with self.subTest(caso=nombre):
                codigo,r=self.pedir_json('POST','/api/simular',cuerpo)
                self.assertEqual(codigo,400);self.assertTrue(r['error'])

    def test_cuerpo_vacio_400_y_demasiado_grande_413(self):
        codigo,_=self.pedir_json('POST','/api/simular',b'')
        self.assertEqual(codigo,400)
        codigo,_=self.pedir_json('POST','/api/simular',b'{"x":"'+b'a'*5000+b'"}')
        self.assertEqual(codigo,413)

    # Rutas y métodos
    def test_ruta_desconocida_404(self):
        for metodo in ['GET','POST']:
            with self.subTest(metodo=metodo):
                codigo,r=self.pedir_json(metodo,'/no-existe',{} if metodo=='POST' else None)
                self.assertEqual(codigo,404);self.assertIn('error',r)

    def test_metodo_no_admitido_405(self):
        for metodo,ruta in [('GET','/api/simular'),('POST','/api/evidencia'),('PUT','/api/simular'),('DELETE','/')]:
            with self.subTest(metodo=metodo,ruta=ruta):
                codigo,r=self.pedir_json(metodo,ruta,{} if metodo!='GET' else None)
                self.assertEqual(codigo,405);self.assertIn('usar',r['error'])

    # Fallas del servidor: 500 con JSON, y el servidor sigue atendiendo
    def test_evidencia_ausente_500(self):
        with self.evidencia_temporal(contenido=False):
            for metodo,ruta,cuerpo in [('GET','/api/evidencia',None),('POST','/api/simular',{'semilla':1})]:
                with self.subTest(ruta=ruta):
                    codigo,r=self.pedir_json(metodo,ruta,cuerpo)
                    self.assertEqual(codigo,500);self.assertIn('No se encontró la evidencia',r['error'])

    def test_evidencia_danada_500(self):
        for nombre,preparar,texto in [('JSON roto',lambda:self.evidencia_temporal('{roto'),'dañada'),
                                      ('no es objeto',lambda:self.evidencia_temporal('[1]'),'no es un objeto'),
                                      ('faltan claves',lambda:self.evidencia_temporal(quitar=['parametros']),'faltan: parametros')]:
            with self.subTest(caso=nombre):
                with preparar():
                    for metodo,ruta,cuerpo in [('GET','/api/evidencia',None),('POST','/api/simular',{'semilla':1})]:
                        codigo,r=self.pedir_json(metodo,ruta,cuerpo)
                        self.assertEqual(codigo,500,ruta);self.assertIn(texto,r['error'])
                shutil.rmtree(self.tmp/'resultados')

    def test_datos_ausentes_o_danados_500(self):
        roto=self.tmp/'roto.csv';roto.write_text('a,b\n1,2\n',encoding='utf-8')
        for nombre,ruta in [('ausentes',self.tmp/'no_existe.csv'),('sin columnas esperadas',roto)]:
            with self.subTest(caso=nombre),mock.patch.object(app,'DATOS',ruta):
                codigo,r=self.pedir_json('POST','/api/simular',{'semilla':1})
                self.assertEqual(codigo,500);self.assertIn('datos',r['error'])
                # La fuente sintética no usa el CSV y sigue funcionando.
                codigo,_=self.pedir_json('POST','/api/simular',{'semilla':1,'fuente':'nhpp'})
                self.assertEqual(codigo,200)

    def test_pagina_ausente_500(self):
        with mock.patch.object(app,'PAGINA',self.tmp/'no_existe.html'):
            codigo,r=self.pedir_json('GET','/')
        self.assertEqual(codigo,500);self.assertIn('web/index.html',r['error'])

    def test_error_interno_inesperado_500_sin_detalles(self):
        with mock.patch.object(app,'simular',side_effect=RuntimeError('detalle interno')),\
             contextlib.redirect_stderr(io.StringIO()) as consola:
            codigo,r=self.pedir_json('POST','/api/simular',{'semilla':1,'fuente':'nhpp'})
        self.assertEqual(codigo,500);self.assertNotIn('detalle interno',r['error'])
        self.assertIn('detalle interno',consola.getvalue())

    def test_se_recupera_despues_de_un_error(self):
        with self.evidencia_temporal(contenido=False):
            self.assertEqual(self.pedir_json('GET','/api/evidencia')[0],500)
        self.assertEqual(self.pedir_json('POST','/api/simular','{malo')[0],400)
        codigo,r=self.pedir_json('POST','/api/simular',{'semilla':100000})
        self.assertEqual(codigo,200)
        self.assertEqual(r['base']['metricas'],self.demo['base']['metricas'])


if __name__=='__main__':unittest.main()
