# Guion de exposición y defensa

Duración objetivo: 13 minutos de exposición y demostración más 2 minutos de preguntas. El reparto es una **propuesta para ensayar**, no un registro de contribuciones realizadas. La presentación editable está en `output/presentacion/presentacion_call_center_entrega.pptx`; las notas de cada diapositiva repiten este guion.

| Tiempo | Diapositiva | Responsable propuesto | Qué explicar |
|---|---|---|---|
| 0:00–0:20 | 1 Portada | Fabian | Tema, integrantes y caso real (banco en Israel, 1999, datos de Technion) |
| 0:20–1:10 | 2 Problema | Fabian | Redistribuir 105 horas nominales en 17 franjas; maximizar atención ≤120 s; límites 1–9 y ±2 |
| 1:10–2:00 | 3 Datos | Fabian | Fuente, filtros y separación noviembre (ajuste) / diciembre (evaluación) |
| 2:00–3:00 | 4 Modelo | Diego | Eventos, prioridad de 90 s, paciencia exponencial, servicio lognormal, disponibilidad 0,725 |
| 3:00–5:00 | 5 Recocido | Diego | Representación, vecino, aceptación exp(−Δ/T), temperatura 2 → 0,02, restricciones |
| 5:00–6:00 | 6 Experimento y verificación | Diego | 60 pares por condición, 600 corridas, IC pareados; 46 pruebas, verificador y manifiesto |
| 6:00–9:00 | 7 Demo | Yehosua | Ejecución normal, demanda 1,4, día sintético, exportación y panel de evidencia |
| 9:00–10:00 | 8 Resultado | Yehosua | 71,67% → 72,94%; +1,27 pp, IC [0,78; 1,76]; sin mejora detectable en espera total ni abandono |
| 10:00–11:00 | 9 Validación | Yehosua | Sesgo de espera −16,44 s; MAE diario 23,41 s; validación parcial |
| 11:00–12:00 | 10 Sensibilidad | Fabian | La ganancia depende de la carga; con demanda −20% empeora el abandono |
| 12:00–13:00 | 11 Conclusión | Diego | Mejora simulada; medir disponibilidad real antes de aplicar el horario |
| 13:00–15:00 | Preguntas | Todos | Responder sin exceder el tiempo |

## Qué decir en cada diapositiva

**1 Portada.** Simulación de eventos discretos más recocido simulado para proponer una distribución de capacidad. Datos históricos de un banco de 1999 publicados por Technion; no representan un call-center guatemalteco actual.

**2 Problema.** 105 es la suma de agentes de las 17 franjas de una hora, no 105 personas. El horario base se infiere de los picos medios de actividad de noviembre. Se conserva el presupuesto, con 1 a 9 agentes por franja y un cambio máximo de 2 respecto de la base. El umbral de 120 s es una definición del estudio, no un contrato del banco. La gráfica dibuja cada capacidad como un escalón que ocupa la hora completa, de 07:00 a 24:00.

**3 Datos.** De 84.084 registros se incluyen 67.563 solicitudes PS, NE y NW, de domingo a jueves entre 07:00 y 24:00, en 44 días. Noviembre aporta 33.548 llamadas en 22 días y define parámetros, calibración y búsqueda; diciembre aporta 34.015 en 22 días y se reserva para evaluación y validación. Las 60 réplicas remuestrean esos 22 días con aleatoriedad nueva; no son 60 días históricos distintos.

**4 Modelo.** Eventos: llegada, fin de servicio, cambio de capacidad y vencimiento de paciencia. La cola ordena por una llegada virtual que resta 90 s a las llamadas prioritarias. Servicio lognormal por tipo; paciencia exponencial con media 376,40 s estimada con censura. Las reducciones de capacidad no interrumpen servicios; a las 24:00 cesan las llegadas y se vacía la cola. Dos métricas de cola: `cola_media` promedia la cola durante la apertura (área entre 07:00 y 24:00 dividida entre 61 200 s) y `area_cola_s` integra hasta el vaciado y cierra la identidad con la suma de esperas.

**5 Recocido.** Vector entero de 17 posiciones. Un vecino traslada una hora-agente de una franja donante a una receptora respetando 1..9, ±2 y suma 105. Mejoras se aceptan; empeoramientos Δ con probabilidad exp(−Δ/T). Enfriamiento geométrico de 2 a 0,02; 400 iteraciones por cada uno de 3 reinicios (semillas 7301, 7302 y 7303); 8 entradas sintéticas de noviembre (semillas 30000 a 30007) comunes a todos los candidatos. Si la base no admite ningún traslado factible, el optimizador la devuelve y registra esa causa de terminación. La elección se hace antes de tocar diciembre.

**6 Experimento y verificación.** Cinco condiciones × dos políticas × 60 semillas nuevas (100000 a 100059): 600 corridas. Cada pareja base-propuesta usa la misma lista de llamadas, así la diferencia tiene menos ruido. IC t de Student de las diferencias pareadas, condicionado a los parámetros y a los 22 días. Verificación interna, distinta de la validación contra la realidad: 46 pruebas automatizadas (motor, optimizador, separación de datos, corridas aisladas, servidor HTTP y coherencia de la entrega); `scripts/verificar_entrega.py` recalcula las 40 diferencias pareadas desde las corridas, comprueba semillas separadas por etapa, presupuesto y límites, hashes de los datos y que README, guion e informe citen las mismas cifras; `resultados/manifiesto.json` registra estado de la corrida, configuración, semillas, versiones y commit del código. Cada corrida se escribe en `.en_curso` y solo al terminar reemplaza `resultados/`.

**7 Demo.** Ver la sección siguiente. Mensaje central: una réplica explica el mecanismo; los 60 pares sostienen la comparación.

**8 Resultado.** La atención oportuna pasa de 71,67% a 72,94%: +1,27 puntos porcentuales, IC 95% [0,78; 1,76]. El cambio relativo es 1,77%, una cantidad distinta. Espera total (54,98 → 54,99 s) y abandono (14,56% → 14,62%) no cambian de forma detectable: sus intervalos incluyen cero. La espera de las llamadas atendidas baja de 50,46 a 47,69 s. Es un resultado del simulador, no una mejora observada en el banco.

**9 Validación.** Espera real media de diciembre 71,42 s frente a 54,98 s simulados: sesgo −16,44 s (23,02%). MAE diario 23,41 s en la comprobación de 30 simulaciones por cada uno de los 22 días. El abandono real es 18,65% frente a 14,56% simulado; la atención oportuna real es 62,96% frente a 71,67% simulada. La capacidad se infiere de la actividad, no de una nómina observada; por eso la validación es parcial.

**10 Sensibilidad.** Atención base/propuesta: demanda −20%: 85,65/85,73; normal: 71,67/72,94; +20%: 54,40/55,98; +40%: 39,70/41,61. Con +40% la diferencia es 1,91 pp, IC [1,54; 2,27]. Con −20% la diferencia es 0,08 pp e incluye cero, mientras el abandono sube 0,45 pp, IC [0,18; 0,72]. Con servicio +15%: 1,84 pp, IC [1,36; 2,32]. No presentar la propuesta como universalmente superior.

**11 Conclusión.** La redistribución mejora la atención dentro del umbral bajo las condiciones simuladas, con las mismas 105 horas nominales. El alcance es exploratorio por la discrepancia con los datos reales y porque no se modelan turnos ni descansos. Siguiente paso: medir disponibilidad real, revisar supuestos y volver a validar antes de un piloto. No se estima ahorro monetario. Se declara el uso de asistencia de IA en el informe.

## Demo preparada

Antes de entrar: activar el entorno, ejecutar `python -m unittest discover -s tests` (46 pruebas en OK) y `python scripts/verificar_entrega.py` (debe empezar con `OK: 600 corridas, 60 réplicas por condición/política`). Luego `python app.py`, abrir `http://127.0.0.1:8765` y comprobar que el panel de evidencia muestra "60 réplicas" y que la primera comparación carga sola. Si el puerto está ocupado, la demo lo avisa al iniciar: usar `python app.py --port 8766`. Tener el PDF del informe y las figuras disponibles sin conexión.

Lo que muestra la pantalla: a la izquierda los controles (fuente de llegadas, demanda, duración de atención, semilla, botón de ejecución y descarga); a la derecha tres indicadores de la réplica (atendidas en ≤120 s, espera total media y abandono, cada uno con el valor de la base y el cambio), la gráfica "Evolución de la cola" con ambas políticas, la gráfica "Capacidad por hora" con los dos horarios escalonados, y más abajo el panel "Evidencia del experimento" con la tabla de validación y el IC pareado de 60 réplicas, que no cambia al mover los controles.

1. Ejecución normal: fuente "Día real de diciembre de 1999", semilla 100000, demanda 1,00×, servicio 1,00×. Es la réplica guardada en `resultados/demo.json` (fecha 1999-12-14, 1.740 solicitudes): atención 60,17% con la base y 65,86% con la propuesta; abandono 20,00% frente a 18,45%. Explicar que la misma lista de llamadas permite comparar capacidad y que es un solo día, con más carga que el promedio.
2. Leer las dos gráficas: la cola crece en las franjas donde la base tiene menos agentes que la propuesta; el horario propuesto mueve capacidad hacia la mañana y la tarde y la quita de la noche. La réplica usa llegadas y tipos reales de esa fecha; servicio, paciencia y prioridad se sortean.
3. Elevar la demanda a 1,40× con la misma semilla y ejecutar. En esta réplica la atención cae a 26,05% con la base y 25,81% con la propuesta, con abandono 40,65% frente a 39,25%: la propuesta pierde en atención y gana en abandono. Usarlo a favor: una réplica individual puede ir en cualquier dirección; por eso la conclusión viene de 60 pares por condición, donde con demanda +40% la mejora media es 1,91 pp. También explicar que el nivel absoluto cae para ambas políticas cuando la carga sube.
4. Opcional, si hay tiempo: cambiar la fuente a "Día sintético ajustado con noviembre" para mostrar que el motor también genera llegadas con el modelo de noviembre; escribir una semilla inválida (por ejemplo 1,5) para mostrar el mensaje de error sin que la demo se caiga.
5. Bajar al panel de evidencia: tabla de validación (referencia real, base y propuesta) y el IC pareado +1,27 pp [0,78; 1,76]. Mostrar el botón "Descargar esta réplica" (JSON con métricas, traza y horarios). No presentar una réplica favorable como prueba estadística.
6. Si falla la demo: abrir `figuras/07_trayectoria.png` (misma réplica, semilla 100000), `figuras/04_sensibilidad.png` y las tablas de `resultados/`. Si la evidencia no carga, la página lo indica en rojo; revisar la consola donde corre `app.py`.

## Preguntas probables

**¿Por qué recocido simulado?** El traslado de una unidad conserva el presupuesto; la aceptación temporal de empeoramientos ayuda a explorar otros candidatos. Es fácil imponer límites. No garantiza el óptimo global.

**¿Qué parte usa datos reales?** Fecha, llegadas y tipos en el replay de diciembre; los tiempos reales de espera y los resultados se usan para validar. Las distribuciones, capacidad y disponibilidad se estiman con noviembre. Paciencia, servicio y prioridad se sortean en las réplicas.

**¿Por qué no se tomó el promedio de paciencia de quienes abandonan?** Quienes reciben atención dejan de revelar su paciencia. Sus esperas son observaciones censuradas. El estimador exponencial usa exposición total dividida entre abandonos, bajo independencia supuesta.

**¿Por qué 120 segundos?** Es una definición de objetivo del estudio. No se afirma que sea un SLA contratado por el banco.

**¿Se ahorra dinero?** No se estiman costos. Se conservan 105 horas nominales; el modelo no asigna turnos, descansos ni personas. Puede haber ocupación transitoria y vaciado después del cierre.

**¿Qué significa +1,27 pp?** Es la resta 72,94% − 71,67%. El cambio relativo es aproximadamente 1,77%, una cantidad distinta.

**¿La propuesta mejora todo?** No. En condición normal mejora la atención dentro del umbral y la espera entre atendidos; no se detecta mejora del abandono o la espera total. Con demanda −20% aumenta el abandono.

**¿Por qué en la demo con demanda 1,4 la propuesta sale peor?** Porque es una sola réplica de un día cargado. La diferencia pareada promedio de 60 pares con demanda +40% es +1,91 pp a favor de la propuesta; una réplica individual puede quedar en cualquier lado de esa media.

**¿Está validado el modelo?** Parcialmente. La base subestima la espera media y el abandono; el MAE diario de espera es 23,41 s. Los IC describen incertidumbre de simulación, no eliminan sesgo del modelo.

**¿Cómo evitaron usar la evaluación para elegir?** Los parámetros, calibración, búsqueda y elección usan noviembre y semillas separadas. Diciembre se reserva para evaluación y validación. Una prueba modifica resultados de diciembre y confirma que el ajuste permanece igual.

**¿Son 60 días reales nuevos?** No. Se remuestrean 22 días reales y se genera aleatoriedad nueva en cada réplica. La independencia corresponde a las semillas computacionales, condicionada a esa distribución empírica.

**¿Cómo saben que la evidencia está completa y es la que dice el informe?** El manifiesto declara estado `completa`, semillas, versiones y commit. El verificador recalcula las 40 diferencias pareadas desde las 600 corridas, comprueba que las semillas de calibración, búsqueda y evaluación no se crucen, que los hashes de los datos coincidan y que README, guion e informe citen las mismas cifras. Una corrida interrumpida queda en `.en_curso` y no se presenta como resultado.

**¿Qué pasa si se les da una entrada absurda al motor o a la demo?** El motor rechaza semillas no enteras o negativas, factores no finitos, disponibilidad fuera de (0, 1] y umbral no positivo. La demo responde JSON con códigos 400, 404, 405, 413 y 500 y la interfaz muestra el mensaje sin cerrarse.

**¿Se usó IA?** Sí, se declara en el informe. La fuente de datos es Technion. El equipo debe explicar y revisar el código y registrar sus aportes reales.
