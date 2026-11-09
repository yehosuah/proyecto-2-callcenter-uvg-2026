# Fuentes y atribución

Consulta: 8 de noviembre de 2026. Fecha de entrega del proyecto: 10 de noviembre de 2026.

1. Ilan Guedj y Avi Mandelbaum. *Anonymous Bank Call-Center Data*, documentación del 9 de febrero de 2000 y registros de 1999. [Página de Technion](https://serveng.technion.ac.il/homeworks/call-center-data/) y [documentación](https://serveng.technion.ac.il/files/Homeworks/callcenterdata/documentation.pdf). Es la fuente de datos y de reglas del sistema, con las simplificaciones indicadas en el informe.
2. Brown, Gans, Mandelbaum, Sakov, Shen, Zeltyn y Zhao (2005). *Statistical Analysis of a Telephone Call Center: A Queueing-Science Perspective*. JASA 100(469), 36–50. [Versión de autor de 2004](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Statistical-analysis2.pdf). Referencia para separar llegadas, servicio y paciencia; no garantiza que los supuestos elegidos sean exactos.
3. Kirkpatrick, Gelatt y Vecchi (1983). *Optimization by Simulated Annealing*. Science 220(4598), 671–680. DOI 10.1126/science.220.4598.671. [Artículo](https://hedibert.org/wp-content/uploads/2013/12/1983KirkpatrickGelattVecchi.pdf). Fundamento del recocido implementado.
4. [SciPy dual_annealing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html). Contraste técnico de una implementación de biblioteca; no se invoca en el proyecto.
5. [NumPy PCG64](https://numpy.org/doc/stable/reference/random/bit_generators/pcg64.html). Generación aleatoria reproducible.
6. [Python heapq](https://docs.python.org/3/library/heapq.html). Agenda de eventos y cola de prioridad.

Los hashes de los ZIP, las URLs directas y los filtros están en `datos/procedencia.json`. El proyecto redistribuye únicamente los CSV depurados sin identificadores de clientes, llamadas, líneas ni nombres de agentes.

## Borrador de notificación de uso

La documentación pide atribución y notificación a Avi Mandelbaum. No se ha enviado ningún mensaje. Verificar el contacto actual en la página oficial antes de enviarlo.

Asunto: Academic use of Anonymous Bank call-center data

Dear Professor Mandelbaum,

We are students at Universidad del Valle de Guatemala. For our Modeling and Simulation course project, we used the November and December 1999 Anonymous Bank call-center records hosted by Technion. We studied a discrete-event simulation of service and abandonment and a simulated annealing procedure for redistributing nominal hourly capacity.

Our report credits Ilan Guedj and Avi Mandelbaum and cites the dataset documentation. We removed customer, call, line and agent identifiers from our project data. We explicitly distinguish simulated improvements from observed outcomes and report the model's validation limitations.

Thank you for making the data available for academic work.

Fabian Prado, Diego Sandoval and Yehosua Hercules
Universidad del Valle de Guatemala
