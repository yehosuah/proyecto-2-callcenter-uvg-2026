# Simulación y optimización de un call-center

Proyecto 2, CC3074 Modelización y Simulación, Universidad del Valle de Guatemala. Entrega: **10 de noviembre de 2026**.

Fabian Prado (23427), Diego Sandoval (231977) y Yehosua Hercules (241452).

Repositorio público: [yehosuah/proyecto-2-callcenter-uvg-2026](https://github.com/yehosuah/proyecto-2-callcenter-uvg-2026).

El proyecto simula atención y abandono en un call-center bancario y busca una redistribución de capacidad mediante recocido simulado. Usa registros públicos de noviembre y diciembre de 1999 del banco anónimo documentado por Technion. La solución conserva 105 horas-agente **nominales** y aumenta la atención en un máximo de 120 segundos de 71,67% a 72,94% dentro del modelo: +1,27 puntos porcentuales, IC pareado del 95% [0,78; 1,76].

La validación externa es parcial: el modelo subestima la espera media real en 16,44 s; el MAE por día es 23,41 s. La mejora es simulada, no una mejora observada en el banco. No hay reducción detectable del abandono ni de la espera total en la condición normal. Con demanda 20% menor empeora el abandono.

## Abrir la entrega

- [Informe PDF](output/pdf/informe_call_center.pdf).
- [Word editable](output/word/informe_call_center.docx), Times New Roman 12, interlineado 1,5.
- [Presentación editable en Spaces](https://chatgpt.com/space/page_bfc0c11534e881918dd52bd4d84631d5); su acceso se administra por separado del repositorio.
- [Guion y defensa](docs/GUION.md).
- [Rúbrica y pendientes](docs/ENTREGA.md).
- [Contribuciones por confirmar](docs/CONTRIBUCIONES.md).

## Ejecutar desde un entorno limpio

**Python 3.9, 3.10, 3.11 o 3.12.** Python 3.13 o posterior no sirve: numpy 2.0.2 no tiene paquetes para esas versiones. Versiones probadas por el equipo:

| Sistema | Python | Qué se hizo |
|---|---|---|
| macOS (Apple Silicon) | 3.9.6 | Generación de los resultados de la entrega (`resultados/manifiesto.json`) |
| Windows 11 | 3.11.8 | Instalación desde cero con `requirements-lock.txt`, pruebas, verificador y demo |

`requirements-lock.txt` fija las 18 dependencias, directas y transitivas, con un mismo conjunto para todas esas versiones de Python, de modo que cada equipo instala exactamente lo mismo. `requirements.txt` solo declara rangos de las dependencias directas; usarlo no garantiza reproducir los resultados.

**macOS o Linux:**

```bash
git clone https://github.com/yehosuah/proyecto-2-callcenter-uvg-2026.git
cd proyecto-2-callcenter-uvg-2026
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python scripts/verificar_entrega.py
python app.py
```

**Windows (PowerShell):** si `python --version` muestra 3.13 o más, usar el lanzador `py` con una versión instalada, por ejemplo 3.11.

```bash
git clone https://github.com/yehosuah/proyecto-2-callcenter-uvg-2026.git
cd proyecto-2-callcenter-uvg-2026
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python scripts/verificar_entrega.py
python app.py
```

Si PowerShell no permite ejecutar `Activate.ps1`, llamar directamente a `.venv\Scripts\python.exe` en lugar de `python`. Si el repositorio está en una carpeta sincronizada (OneDrive, iCloud), conviene crear el entorno fuera de ella, por ejemplo `py -3.11 -m venv C:\Users\<usuario>\.venvs\callcenter`, para no sincronizar miles de archivos.

Resultado esperado: todas las pruebas en `OK` y el verificador empieza con `OK: 600 corridas, 60 réplicas por condición/política`. Si en Windows el verificador indica que el hash de `datos/*.csv` no coincide, el clon es anterior a `.gitattributes` y tiene finales de línea CRLF: con el árbol limpio, borrar los CSV de `datos/` y ejecutar `git checkout -- datos/`.

Abrir `http://127.0.0.1:8765`. La demo funciona sin conexión a internet una vez instaladas las dependencias. Si el puerto está ocupado, la demo lo indica al iniciar; usar `python app.py --port 8766` o cerrar la otra con Ctrl+C. Para abrirla con otra corrida: `python app.py --resultados <carpeta>`.

La demo usa el mismo simulador que los experimentos. Permite cambiar semilla, factor de demanda y duración de servicio. Compara ambas políticas sobre idénticas llamadas y exporta la réplica a JSON. Una ejecución individual ilustra el mecanismo; las conclusiones provienen de 60 réplicas por política y condición.

## Reproducir la evidencia

Los CSV depurados y todos los resultados están incluidos. No hace falta descargar de nuevo la fuente para ejecutar la demo o los experimentos.

```bash
python experimentos.py --repeticiones 60 --iteraciones 400
python figuras.py
python informe.py
python scripts/verificar_entrega.py
```

El experimento completo tarda alrededor de un minuto (`segundos_ejecucion` en el manifiesto); puede variar según el equipo. Escribe primero en `resultados.en_curso/` y solo al terminar reemplaza `resultados/`, que queda como `resultados.anterior/`; una corrida interrumpida no se presenta como completa. `--salida <carpeta>` permite correr en otra carpeta, que luego se revisa con `python scripts/verificar_entrega.py --resultados <carpeta>` y `python informe.py --resultados <carpeta> --salida <archivo.docx>`. Regenera parámetros, calibración, búsqueda, 600 corridas finales y validación por fecha. La calibración tiene 30 réplicas por valor; la validación adicional tiene 30 réplicas en cada uno de 22 días. Las ocho entradas usadas durante la búsqueda no sustituyen las 60 réplicas finales independientes.

`informe.py` genera el Word; abrirlo en Microsoft Word o LibreOffice y exportar como PDF a `output/pdf/informe_call_center.pdf`. Para exportar desde una instalación local de LibreOffice:

```bash
soffice --headless --convert-to pdf --outdir output/pdf output/word/informe_call_center.docx
```

La fuente Times New Roman debe estar instalada para conservar el formato solicitado. Las gráficas usan Times New Roman cuando está disponible y DejaVu Serif como respaldo. Los resultados numéricos no dependen de la fuente tipográfica.

## Datos y trazabilidad

Fuente: [Guedj y Mandelbaum, Technion](https://serveng.technion.ac.il/homeworks/call-center-data/), [documentación](https://serveng.technion.ac.il/files/Homeworks/callcenterdata/documentation.pdf). Se usan 67.563 solicitudes de agente PS, NE y NW, de domingo a jueves entre las 07:00 y las 24:00, provenientes de 84.084 registros originales. Noviembre: 33.548 solicitudes y 22 días. Diciembre: 34.015 solicitudes y 22 días.

`datos/procedencia.json` registra URLs, SHA-256, conteos y cada filtro. Se eliminaron identificadores de clientes, llamadas, líneas y agentes. Los archivos brutos no se redistribuyen. La documentación permite el uso y solicita atribución y notificación; hay un borrador de notificación en `docs/FUENTES.md`, aún no enviado.

```bash
python scripts/preparar_datos.py
# Alternativa con ZIP originales ya descargados:
python scripts/preparar_datos.py --cache /ruta/al/directorio
```

La descarga comprueba los hashes esperados y se detiene si la fuente cambió. No desactivar esa comprobación sin revisar el cambio.

## Modelo y diseño experimental

- Eventos discretos: llegadas, finalizaciones, cambios de capacidad y abandono.
- Entrenamiento: intensidad horaria Poisson con factor Gamma diario; servicio lognormal por tipo; paciencia exponencial estimada con censura; prioridad virtual de 90 s.
- Capacidad base inferida de picos de actividad, no horarios reales. Disponibilidad efectiva 0,725 calibrada solo con noviembre.
- Recocido simulado: 400 iteraciones, 3 reinicios, temperaturas 2 a 0,02; traslado de una hora-agente entre franjas; presupuesto 105, capacidad 1–9 y máximo ±2 frente a la base.
- Evaluación: cinco condiciones, dos políticas, 60 semillas distintas por condición. Llegadas y tipos de diciembre; servicio, paciencia y prioridad sorteados con parámetros de noviembre. Las políticas comparten llamadas dentro de cada pareja.
- IC de Student sobre diferencias pareadas. La incertidumbre es condicional al modelo y a los 22 días observados; no incorpora toda la incertidumbre de parámetros o de generalización.
- Al bajar capacidad no se interrumpen servicios; puede haber ocupación transitoria por encima del nuevo valor. Las horas nominales no equivalen a costo laboral real ni a turnos individuales.

## Archivos principales

| Ruta | Función |
|---|---|
| `src/modelo.py` | Generación de entradas, eventos y métricas |
| `src/ajuste.py` | Parámetros usando únicamente noviembre |
| `src/optimizacion.py` | Recocido, restricciones y registro de búsqueda |
| `experimentos.py` | Calibración, búsqueda, evaluación y validación |
| `app.py`, `web/` | Demo local |
| `scripts/` | Preparación y verificación de datos y resultados |
| `tests/` | Casos manuales, aislamiento temporal, reproducción de demo, rutas HTTP y coherencia de la evidencia |
| `resultados/` | Corridas individuales, medias, dispersión, IC y manifiesto |
| `figuras/` | Siete gráficas exportadas a PNG y PDF |
| `informe.py`, `src/documento.py` | Contenido y formato de Word |

## Atribución y uso de IA

La bibliografía completa está en el informe y en `docs/FUENTES.md`. El simulador y el recocido están implementados explícitamente; no se llama una función de optimización de SciPy. SciPy se usa para cuantiles t; NumPy para aleatoriedad; pandas para tablas y Matplotlib para figuras.

Se usó asistencia de OpenAI Codex para investigación, preparación, programación, ejecución, pruebas y redacción. Los datos reales provienen de Technion. La asistencia no acredita aportes individuales: cada integrante debe revisar, comprender y confirmar sus contribuciones antes de entregar.
