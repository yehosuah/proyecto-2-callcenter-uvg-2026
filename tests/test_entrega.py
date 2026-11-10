import contextlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from app import comparar
from experimentos import resumen, METRICAS
from src.ajuste import parametros_desde_datos
from scripts.verificar_entrega import (EvidenciaInvalida, verificar_resultados, verificar_documentos,
                                       METRICAS_VALIDACION, main as verificar_main)

ROOT=Path(__file__).resolve().parents[1]


def leer(ruta):return json.loads(Path(ruta).read_text(encoding='utf-8'))
def escribir(ruta,obj):Path(ruta).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')


def subconjunto(destino,n):
    """Copia resultados/ y la reduce a las primeras n semillas, recalculando todo lo que depende de ellas.

    Reproduce una corrida consistente con --repeticiones n sin volver a simular.
    """
    shutil.copytree(ROOT/'resultados',destino)
    man=leer(destino/'manifiesto.json');semillas=man['semillas_evaluacion'][:n]
    runs=pd.read_csv(destino/'repeticiones.csv');runs=runs[runs.semilla.isin(semillas)].reset_index(drop=True)
    runs.to_csv(destino/'repeticiones.csv',index=False)
    tab=[dict(escenario=e,politica=pol,metrica=m,**resumen(g[m])) for (e,pol),g in runs.groupby(['escenario','politica']) for m in METRICAS]
    pd.DataFrame(tab).to_csv(destino/'resumen.csv',index=False)
    dif=[]
    for e,g in runs.groupby('escenario'):
        b=g[g.politica=='base'].set_index('semilla');o=g[g.politica=='mejorada'].set_index('semilla')
        for m in METRICAS:
            dif.append(dict(escenario=e,metrica=m,**resumen(o[m]-b[m]),
                cambio_relativo_pct=100*(o[m].mean()-b[m].mean())/b[m].mean() if b[m].mean() else 0.0))
    pd.DataFrame(dif).to_csv(destino/'diferencias_pareadas.csv',index=False)
    ref=pd.read_csv(destino/'referencia_diaria.csv');rd=ref[ref.fecha.str.startswith('1999-12')]
    normal=runs[runs.escenario=='normal'];valid=[]
    for m in METRICAS_VALIDACION:
        obs=float(rd[m].mean());sb=float(normal[normal.politica=='base'][m].mean());so=float(normal[normal.politica=='mejorada'][m].mean())
        valid.append(dict(metrica=m,referencia_diciembre=obs,simulacion_base=sb,simulacion_mejorada=so,
            error_absoluto_base=abs(sb-obs),error_relativo_base_pct=100*abs(sb-obs)/abs(obs),
            cambio_absoluto=so-sb,cambio_relativo_pct=100*(so-sb)/sb))
    pd.DataFrame(valid).to_csv(destino/'validacion.csv',index=False)
    r=leer(destino/'resumen.json');r.update(repeticiones=n,resumen=tab,diferencias=dif,validacion=valid)
    escribir(destino/'resumen.json',r)
    man['semillas_evaluacion']=semillas;man['configuracion']['repeticiones']=n
    escribir(destino/'manifiesto.json',man)
    return destino


def texto_word(ruta):
    from docx import Document
    d=Document(ruta)
    return '\n'.join([p.text for p in d.paragraphs]+[c.text for t in d.tables for fila in t.rows for c in fila.cells])


class EntregaTest(unittest.TestCase):
    def test_demo_reproduce_replica_guardada(self):
        r=comparar({'semilla':100000})
        saved=json.loads((ROOT/'resultados/demo.json').read_text(encoding='utf-8'))
        for politica in ['base','mejorada']:
            self.assertEqual(r[politica]['metricas'],saved[politica]['metricas'])
            self.assertEqual(r[politica]['traza'],saved[politica]['traza'])

    def test_entradas_invalidas_demo(self):
        for x in [None,[],{'semilla':1.5},{'semilla':True},{'semilla':-1},
                  {'demanda':float('nan')},{'servicio':3},{'fuente':'otra'}]:
            with self.subTest(entrada=x):
                with self.assertRaises(ValueError):comparar(x)

    def test_ajuste_no_depende_de_diciembre(self):
        d=pd.read_csv(ROOT/'datos/llamadas_sin_identificadores.csv')
        c=pd.read_csv(ROOT/'datos/concurrencia_observada.csv')
        esperado=parametros_desde_datos(d,c)
        d.loc[d.fecha.str.startswith('1999-12'),['servicio_s','espera_s']]=999999
        c.loc[c.fecha.str.startswith('1999-12'),'pico_ocupados']=1000
        self.assertEqual(esperado,parametros_desde_datos(d,c))


class EvidenciaTest(unittest.TestCase):
    """D1: los conteos salen de los resultados; un conjunto incompleto o mezclado falla."""

    @classmethod
    def setUpClass(cls):
        cls._tmp=tempfile.TemporaryDirectory();cls.tmp=Path(cls._tmp.name)
        cls.r30=subconjunto(cls.tmp/'r30',30)

    @classmethod
    def tearDownClass(cls):cls._tmp.cleanup()

    def copia(self,nombre):
        destino=self.tmp/nombre;shutil.copytree(self.r30,destino);return destino

    def test_entrega_actual_de_60_pasa(self):
        info=verificar_resultados(ROOT/'resultados')
        self.assertEqual((info['repeticiones'],info['corridas'],info['diferencias']),(60,600,40))

    def test_conjunto_consistente_de_30_pasa_y_se_describe_como_30(self):
        info=verificar_resultados(self.r30)
        self.assertEqual((info['repeticiones'],info['corridas']),(30,300))
        salida=io.StringIO()
        with contextlib.redirect_stdout(salida):codigo=verificar_main(['--resultados',str(self.r30)])
        self.assertEqual(codigo,0)
        self.assertIn('300 corridas, 30 réplicas',salida.getvalue())

    def test_informe_de_30_no_dice_60(self):
        import informe
        docx=self.tmp/'informe_30.docx'
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            informe.main(['--resultados',str(self.r30),'--salida',str(docx)])
        texto=texto_word(docx)
        self.assertIn('30 réplicas',texto)
        self.assertIn('300 comparaciones individuales',texto)
        self.assertIn('100000-100029',texto)
        self.assertNotRegex(texto,r'\b60 (réplicas|semillas|cada una)')
        self.assertNotRegex(texto,r'(?<![\d,])600 (comparaciones|corridas)')
        self.assertNotRegex(texto,r'\{[^{}]+\}')

    def test_conjuntos_incompletos_o_mezclados_fallan(self):
        def quitar_fila(c):
            runs=pd.read_csv(c/'repeticiones.csv');runs.iloc[1:].to_csv(c/'repeticiones.csv',index=False)
        def quitar_condicion(c):
            runs=pd.read_csv(c/'repeticiones.csv');runs[runs.escenario!='demanda_140'].to_csv(c/'repeticiones.csv',index=False)
        def resumen_de_60(c):shutil.copy(ROOT/'resultados/resumen.json',c/'resumen.json')
        def diferencias_de_60(c):shutil.copy(ROOT/'resultados/diferencias_pareadas.csv',c/'diferencias_pareadas.csv')
        def manifiesto_de_60(c):shutil.copy(ROOT/'resultados/manifiesto.json',c/'manifiesto.json')
        def corridas_de_60(c):shutil.copy(ROOT/'resultados/repeticiones.csv',c/'repeticiones.csv')
        def semilla_distinta_en_pareja(c):
            runs=pd.read_csv(c/'repeticiones.csv')
            i=runs[(runs.escenario=='normal')&(runs.politica=='mejorada')].index[0];runs.loc[i,'semilla']=999999
            runs.to_csv(c/'repeticiones.csv',index=False)
        def metrica_alterada(c):
            runs=pd.read_csv(c/'repeticiones.csv');runs.loc[0,'sla_pct']+=1;runs.to_csv(c/'repeticiones.csv',index=False)
        def corrida_en_curso(c):
            m=leer(c/'manifiesto.json');m['estado']='en_curso';escribir(c/'manifiesto.json',m)
        def falta_archivo(c):(c/'validacion.csv').unlink()
        casos={'falta una corrida':quitar_fila,'falta una condición':quitar_condicion,
               'resumen.json de otra corrida':resumen_de_60,'diferencias de otra corrida':diferencias_de_60,
               'manifiesto de otra corrida':manifiesto_de_60,'corridas de otra corrida':corridas_de_60,
               'pareja con semillas distintas':semilla_distinta_en_pareja,'métrica alterada':metrica_alterada,
               'corrida en curso':corrida_en_curso,'falta un archivo':falta_archivo}
        for i,(nombre,mutar) in enumerate(casos.items()):
            with self.subTest(caso=nombre):
                c=self.copia(f'mut{i}');mutar(c)
                with self.assertRaises(EvidenciaInvalida):verificar_resultados(c)

    def test_menos_de_30_replicas_falla_aunque_sea_consistente(self):
        with self.assertRaises(EvidenciaInvalida):verificar_resultados(subconjunto(self.tmp/'r29',29))

    def test_documentos_con_cifras_desactualizadas_fallan(self):
        info=verificar_resultados(ROOT/'resultados')
        raiz=self.tmp/'docs';(raiz/'docs').mkdir(parents=True);(raiz/'output/word').mkdir(parents=True)
        for f in ['README.md','docs/GUION.md','output/word/informe_call_center.docx']:shutil.copy(ROOT/f,raiz/f)
        verificar_documentos(info,raiz)
        readme=(raiz/'README.md').read_text(encoding='utf-8')
        for nombre,cambio in {'otro número de réplicas':('60 réplicas por política','50 réplicas por política'),
                              'cifra desactualizada':('+1,27 puntos','+1,31 puntos')}.items():
            with self.subTest(caso=nombre):
                self.assertIn(cambio[0],readme)
                (raiz/'README.md').write_text(readme.replace(*cambio),encoding='utf-8')
                with self.assertRaises(EvidenciaInvalida):verificar_documentos(info,raiz)
        (raiz/'README.md').write_text(readme,encoding='utf-8')

    def test_interfaz_toma_las_replicas_de_la_evidencia(self):
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        self.assertNotRegex(html,r'\d+ réplicas')
        self.assertIn("$('nrep').textContent=r.repeticiones",html)
        self.assertIn("$('ndias').textContent=r.dias_diciembre",html)


if __name__=='__main__':unittest.main()
