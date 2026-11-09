# Entrega del 10 de noviembre de 2026

Repositorio publicado: [yehosuah/proyecto-2-callcenter-uvg-2026](https://github.com/yehosuah/proyecto-2-callcenter-uvg-2026). El código, los datos depurados, la evidencia y los informes están disponibles públicamente. El enlace de la presentación en Spaces mantiene permisos independientes.

## Evidencia frente a la rúbrica

| Criterio | Evidencia preparada |
|---|---|
| Problema real y justificación | Informe, sección 1; fuente Technion |
| Técnica adicional | Informe, sección 5; `src/optimizacion.py`; referencias académicas |
| Formulación del modelo | Informe, secciones 3 y 4; `src/modelo.py` |
| Simulación funcional | `app.py`; README; doce pruebas automatizadas |
| Mejora implementada | Presupuesto y límites verificados; `resultados/dotacion.csv` |
| Diseño y validación | 600 corridas finales, semillas, SD e IC; validación de 22 fechas |
| Comparación con datos reales | `resultados/validacion.csv` y `validacion_por_dia.csv`; error cuantificado |
| Resultados y conclusiones | Informe, secciones 7–13; siete gráficas y tablas numéricas |
| Presentación y dominio | Diapositivas, demo y guion de 15 minutos con participación propuesta |

## Pendientes que requieren al equipo

1. Confirmar la aprobación docente del tema y que eventos discretos es una técnica vista en clase y recocido simulado corresponde al componente adicional.
2. Completar contribuciones reales y regenerar el Word y PDF. No entregar la tabla pendiente como registro definitivo.
3. Enviar la notificación de uso solicitada por la fuente, usando el borrador de `FUENTES.md` después de revisarlo.
4. Ensayar con cronómetro, ejecutar la demo sin internet y comprobar que todos puedan explicar el modelo y sus límites.

Estos puntos no cambian los resultados calculados. La validación parcial se conserva como hallazgo del trabajo; no debe sustituirse por una afirmación de implementación real.

## Propuesta breve para aprobación del tema

Se propone simular un call-center bancario utilizando registros públicos de Technion de noviembre y diciembre de 1999. Mediante eventos discretos se modelarán llegadas, espera, atención y abandono. Como técnica adicional se implementará recocido simulado para redistribuir una capacidad nominal fija por hora. Se evaluarán atención dentro de 120 segundos, abandono y espera, con separación temporal de datos, al menos 30 repeticiones por condición y comparación cuantitativa contra los registros reales. El análisis reconocerá que la dotación es inferida y que una mejora simulada no prueba una mejora operativa.
