import unittest
import numpy as np
from src.modelo import Llamada,simular,validar_dotacion,generar_llamadas,generar_replay
from src.optimizacion import optimizar

NAN=float('nan');INF=float('inf')
PARAMETROS=dict(llegadas_hora=[2.0]*17,cv2_demanda_diaria=0.0,mezcla_tipos={'PS':1.0},
    servicio={'PS':dict(mu=4.0,sigma=0.5)},paciencia_media_s=300.0,fraccion_prioritaria=0.5)
DIAS={'1999-12-01':[(10.0,'PS'),(20.0,'PS')]}


class ModeloTest(unittest.TestCase):
    def test_caso_manual_con_abandono(self):
        r=simular([Llamada(0,10,100),Llamada(1,5,100),Llamada(2,2,3)],[1]*17,traza=True)
        self.assertEqual([x['espera'] for x in r['llamadas']],[0,9,3])
        self.assertEqual(r['metricas']['atendidas'],2)
        self.assertEqual(r['metricas']['abandonadas'],1)
        self.assertAlmostEqual(r['metricas']['espera_media_s'],4)

    def test_prioridad_adelanta_90_segundos_sin_interrumpir(self):
        r=simular([Llamada(0,100,500),Llamada(10,10,500),Llamada(20,10,500,True)],[1]*17,traza=True)
        self.assertEqual([x['espera'] for x in r['llamadas']],[0,100,80])

    def test_fin_al_vencer_paciencia(self):
        r=simular([Llamada(0,10,50),Llamada(5,2,5)],[1]*17)
        self.assertEqual(r['metricas']['atendidas'],2)

    def test_reduccion_no_interrumpe_y_aumento_descola(self):
        r=simular([Llamada(3590,100,1000),Llamada(3591,100,1000),Llamada(3601,10,1000)], [2]+[1]*16,traza=True)
        self.assertEqual(r['llamadas'][2]['espera'],90)
        r=simular([Llamada(3590,100,1000),Llamada(3591,10,1000)],[1]+[2]*16,traza=True)
        self.assertEqual(r['llamadas'][1]['espera'],9)

    def test_vaciado_y_conservacion(self):
        r=simular([Llamada(61199,121,100)],[1]*17)
        self.assertEqual(r['metricas']['atendidas'],1)
        self.assertAlmostEqual(r['metricas']['extra_min'],2)
        self.assertAlmostEqual(r['metricas']['trabajo_horas'],121/3600)

    def test_capacidad_sobrante_elimina_espera(self):
        r=simular([Llamada(0,10,0),Llamada(0,10,0)],[2]*17)
        self.assertEqual(r['metricas']['espera_media_s'],0)
        self.assertEqual(r['metricas']['sla_pct'],100)

    def test_factibilidad_y_casos_invalidos(self):
        with self.assertRaises(ValueError):validar_dotacion([2]*17,33)
        with self.assertRaises(ValueError):validar_dotacion([1.1]*17)
        with self.assertRaises(ValueError):simular([Llamada(0,-1,10)],[1]*17)
        self.assertEqual(simular([],[1]*17)['metricas']['llamadas'],0)

    def test_optimizador_conserva_presupuesto(self):
        r=optimizar([2]*17,[[Llamada(3600+i,100,1000) for i in range(30)]],1,19,20)
        self.assertEqual(sum(r['dotacion']),34)
        self.assertLessEqual(r['costo'],r['costo_base'])
        self.assertTrue(all(1<=c<=4 for c in r['dotacion']))

    def test_no_modifica_llamadas(self):
        llamadas=[Llamada(0,10,100),Llamada(3,5,30)]
        a=simular(llamadas,[1]*17);b=simular(llamadas,[1]*17)
        self.assertEqual(a,b)

    def test_rechaza_umbral_y_disponibilidad_no_finitos(self):
        llamadas=[Llamada(0,10,100)]
        for u in [NAN,INF,0,-1]:
            with self.subTest(umbral=u):
                with self.assertRaises(ValueError):simular(llamadas,[1]*17,umbral_s=u)
        for d in [NAN,INF,0,-.1,1.5]:
            with self.subTest(disponibilidad=d):
                with self.assertRaises(ValueError):simular(llamadas,[1]*17,disponibilidad=d)
        self.assertEqual(simular(llamadas,[1]*17,umbral_s=1e9)['metricas']['sla_pct'],100)

    def test_generadores_rechazan_factores_no_finitos(self):
        for demanda,servicio in [(NAN,1),(INF,1),(-.1,1),(1,NAN),(1,INF),(1,0),(1,-1)]:
            with self.subTest(demanda=demanda,servicio=servicio):
                with self.assertRaises(ValueError):generar_llamadas(PARAMETROS,1,demanda,servicio)
                with self.assertRaises(ValueError):generar_replay(DIAS,PARAMETROS,1,demanda,servicio)
        self.assertTrue(len(generar_llamadas(PARAMETROS,1,0.0))==0)
        self.assertEqual(generar_replay(DIAS,PARAMETROS,1)[0],'1999-12-01')

    def test_generadores_rechazan_semillas_invalidas(self):
        for semilla in [1.5,True,-1,NAN,'7',None]:
            with self.subTest(semilla=semilla):
                with self.assertRaises(ValueError):generar_llamadas(PARAMETROS,semilla)
                with self.assertRaises(ValueError):generar_replay(DIAS,PARAMETROS,semilla)
        for semilla in [0,5,np.int64(5)]:
            with self.subTest(semilla=semilla):
                self.assertEqual(generar_llamadas(PARAMETROS,semilla),generar_llamadas(PARAMETROS,int(semilla)))


if __name__=='__main__':unittest.main()
