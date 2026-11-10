import json
import tempfile
import unittest
from pathlib import Path
from experimentos import preparar_salida, manifiesto_inicial, escribir_manifiesto, finalizar_salida, referencia_codigo


def _corrida(trabajo,estado,archivo):
    (trabajo/archivo).write_text('x')
    escribir_manifiesto(trabajo,dict(estado=estado))


class ExperimentosTest(unittest.TestCase):
    def setUp(self):
        self._tmp=tempfile.TemporaryDirectory();self.tmp=Path(self._tmp.name)

    def tearDown(self):self._tmp.cleanup()

    def test_preparar_salida_crea_directorio_de_trabajo_aparte(self):
        salida=self.tmp/'res';trabajo=preparar_salida(salida)
        self.assertEqual(trabajo,self.tmp/'res.en_curso')
        self.assertTrue(trabajo.is_dir() and not any(trabajo.iterdir()))
        self.assertFalse(salida.exists())
        with self.assertRaises(RuntimeError):preparar_salida(salida)

    def test_manifiesto_inicial_registra_configuracion_versiones_y_codigo(self):
        m=manifiesto_inicial(repeticiones=30,iteraciones=5,salida=self.tmp/'res')
        self.assertEqual(m['estado'],'en_curso')
        self.assertEqual(m['configuracion']['repeticiones'],30)
        self.assertEqual(m['configuracion']['iteraciones'],5)
        self.assertEqual(len(m['semillas_evaluacion']),30)
        for k in ['python','numpy','pandas','scipy']:self.assertIn(k,m['versiones'])
        for k in ['commit','rama','cambios_sin_confirmar']:self.assertIn(k,m['codigo'])
        self.assertIn('inicio',m)
        json.dumps(m,allow_nan=False)
        self.assertEqual(set(referencia_codigo()),{'commit','rama','cambios_sin_confirmar'})

    def test_finalizar_solo_acepta_corridas_completas(self):
        salida=self.tmp/'res';salida.mkdir();(salida/'viejo.csv').write_text('v')
        trabajo=preparar_salida(salida);_corrida(trabajo,'en_curso','nuevo.csv')
        with self.assertRaises(RuntimeError):finalizar_salida(trabajo,salida)
        self.assertEqual(sorted(p.name for p in salida.iterdir()),['viejo.csv'])
        self.assertTrue(trabajo.is_dir())
        _corrida(trabajo,'completa','nuevo.csv')
        anterior=finalizar_salida(trabajo,salida)
        self.assertEqual(sorted(p.name for p in salida.iterdir()),['manifiesto.json','nuevo.csv'])
        self.assertEqual(anterior,self.tmp/'res.anterior')
        self.assertEqual(sorted(p.name for p in anterior.iterdir()),['viejo.csv'])
        self.assertFalse(trabajo.exists())

    def test_finalizar_sin_corrida_previa_no_deja_anterior(self):
        salida=self.tmp/'res';trabajo=preparar_salida(salida);_corrida(trabajo,'completa','a.csv')
        self.assertIsNone(finalizar_salida(trabajo,salida))
        self.assertFalse((self.tmp/'res.anterior').exists())

    def test_dos_corridas_en_carpetas_distintas_no_se_pisan(self):
        a,b=self.tmp/'a',self.tmp/'b'
        ta,tb=preparar_salida(a),preparar_salida(b)
        _corrida(ta,'completa','solo_a.csv');_corrida(tb,'completa','solo_b.csv')
        finalizar_salida(ta,a);finalizar_salida(tb,b)
        self.assertEqual(sorted(p.name for p in a.iterdir()),['manifiesto.json','solo_a.csv'])
        self.assertEqual(sorted(p.name for p in b.iterdir()),['manifiesto.json','solo_b.csv'])


if __name__=='__main__':unittest.main()
