# Guion de exposición y defensa

Duración objetivo: 13 minutos de exposición y demostración más 2 minutos de preguntas. El reparto es una **propuesta para ensayar**, no un registro de contribuciones realizadas.

| Tiempo | Diapositiva | Responsable propuesto | Qué explicar |
|---|---|---|---|
| 0:00–0:20 | 1 Portada | Fabian | Tema, integrantes y caso real |
| 0:20–1:10 | 2 Problema | Fabian | Redistribuir 105 horas nominales; maximizar atención ≤120 s |
| 1:10–2:00 | 3 Datos | Fabian | Fuente, filtros y separación noviembre/diciembre |
| 2:00–3:00 | 4 Modelo | Diego | Eventos, prioridad, paciencia y servicio |
| 3:00–5:00 | 5 Recocido | Diego | Representación, vecino, aceptación, temperatura y restricciones |
| 5:00–6:00 | 6 Experimento | Diego | Semillas nuevas, 60 pares, IC y pruebas internas |
| 6:00–9:00 | 7 Demo | Yehosua | Ejecución normal, demanda +40%, comparación y exportación |
| 9:00–10:00 | 8 Resultado | Yehosua | 71,67% → 72,94%; +1,27 pp, IC [0,78; 1,76] |
| 10:00–11:00 | 9 Validación | Yehosua | Sesgo de espera −16,44 s; MAE 23,41 s; alcance parcial |
| 11:00–12:00 | 10 Sensibilidad | Fabian | La ganancia depende de la carga; empeora abandono con baja demanda |
| 12:00–13:00 | 11 Conclusión | Diego | Mejorar medición de disponibilidad antes de aplicar el horario |
| 13:00–15:00 | Preguntas | Todos | Responder sin exceder el tiempo |

## Demo preparada

Antes de entrar: activar el entorno, ejecutar `python app.py`, abrir `http://127.0.0.1:8765` y comprobar que las gráficas cargan. Tener el PDF y `resultados/demo.json` disponibles sin conexión.

1. Fuente diciembre, semilla 100000, demanda 1, servicio 1. Ejecutar ambas políticas. Explicar que la misma lista de llamadas permite comparar capacidad.
2. Mostrar cola, ocupación y horario. La réplica usa una fecha real para llegadas, pero servicio y paciencia son sorteados.
3. Cambiar demanda a 1,4 sin cambiar la semilla; ejecutar. Explicar que el nivel absoluto puede caer aunque la propuesta supere a la base.
4. Mostrar el panel de evidencia de 60 réplicas y el botón de descarga. No presentar una réplica favorable como prueba estadística.
5. Si falla la demo, abrir las figuras `07_trayectoria.png`, `04_sensibilidad.png` y las tablas guardadas. No depender de la conexión para mostrar resultados.

## Preguntas probables

**¿Por qué recocido simulado?** El traslado de una unidad conserva el presupuesto; la aceptación temporal de empeoramientos ayuda a explorar otros candidatos. Es fácil imponer límites. No garantiza el óptimo global.

**¿Qué parte usa datos reales?** Fecha, llegadas y tipos en el replay de diciembre; los tiempos reales de espera y los resultados se usan para validar. Las distribuciones, capacidad y disponibilidad se estiman con noviembre. Paciencia, servicio y prioridad se sortean en las réplicas.

**¿Por qué no se tomó el promedio de paciencia de quienes abandonan?** Quienes reciben atención dejan de revelar su paciencia. Sus esperas son observaciones censuradas. El estimador exponencial usa exposición total dividida entre abandonos, bajo independencia supuesta.

**¿Por qué 120 segundos?** Es una definición de objetivo del estudio. No se afirma que sea un SLA contratado por el banco.

**¿Se ahorra dinero?** No se estiman costos. Se conservan 105 horas nominales; el modelo no asigna turnos, descansos ni personas. Puede haber ocupación transitoria y vaciado después del cierre.

**¿Qué significa +1,27 pp?** Es la resta 72,94% − 71,67%. El cambio relativo es aproximadamente 1,77%, una cantidad distinta.

**¿La propuesta mejora todo?** No. En condición normal mejora la atención dentro del umbral y la espera entre atendidos; no se detecta mejora del abandono o la espera total. Con demanda −20% aumenta el abandono.

**¿Está validado el modelo?** Parcialmente. La base subestima la espera media y el abandono; el MAE diario de espera es 23,41 s. Los IC describen incertidumbre de simulación, no eliminan sesgo del modelo.

**¿Cómo evitaron usar la evaluación para elegir?** Los parámetros, calibración, búsqueda y elección usan noviembre y semillas separadas. Diciembre se reserva para evaluación y validación. Una prueba modifica resultados de diciembre y confirma que el ajuste permanece igual.

**¿Son 60 días reales nuevos?** No. Se remuestrean 22 días reales y se genera aleatoriedad nueva en cada réplica. La independencia corresponde a las semillas computacionales, condicionada a esa distribución empírica.

**¿Se usó IA?** Sí, se declara en el informe. La fuente de datos es Technion. El equipo debe explicar y revisar el código y registrar sus aportes reales.
