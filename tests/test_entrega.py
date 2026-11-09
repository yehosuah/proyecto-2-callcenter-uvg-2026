import json
import unittest
from pathlib import Path
import pandas as pd
from app import comparar
from src.ajuste import parametros_desde_datos

ROOT=Path(__file__).resolve().parents[1]


class EntregaTest(unittest.TestCase):
    def test_demo_reproduce_replica_guardada(self):
        r=comparar({'semilla':100000})
        saved=json.loads((ROOT/'resultados/demo.json').read_text())
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


if __name__=='__main__':unittest.main()
