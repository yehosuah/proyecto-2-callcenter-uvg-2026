import unittest
from figuras import escalones_horarios


class FigurasTest(unittest.TestCase):
    def test_escalones_cubren_cada_hora_hasta_las_24(self):
        capacidades=list(range(1,18))
        x,y=escalones_horarios(range(7,24),capacidades)
        self.assertEqual(list(x),list(range(7,25)))
        self.assertEqual(list(y),capacidades+[17])
        # Each capacity owns exactly [h, h+1): the value at edge h is dotacion[h-7].
        for h,c in zip(range(7,24),capacidades):
            self.assertEqual(y[x.index(h)],c)

    def test_escalones_requieren_17_horas(self):
        with self.assertRaises(ValueError):escalones_horarios(range(7,23),[1]*16)
        with self.assertRaises(ValueError):escalones_horarios(range(7,24),[1]*16)


if __name__=='__main__':unittest.main()
