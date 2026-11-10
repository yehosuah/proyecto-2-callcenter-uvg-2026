"""Informe Word convencional calculado desde resultados; exportar el DOCX a PDF.

Todas las cifras del texto se leen de la carpeta de resultados verificada. Si los
resultados contradicen una afirmación cualitativa del texto, el informe no se genera.

Uso:
    python informe.py
    python informe.py --resultados otra_corrida --salida tmp/informe.docx
"""
from pathlib import Path
from xml.sax.saxutils import escape
import argparse
import csv
import json
import sys
from src.documento import InformeWord
from scripts.verificar_entrega import verificar_resultados

ROOT=Path(__file__).resolve().parent
cm=1
NUMEROS={2:'dos',3:'tres',4:'cuatro',5:'cinco',6:'seis',7:'siete',8:'ocho',9:'nueve',10:'diez'}


def fmt(x,d=2):
    """Formato del informe: espacio para miles y coma decimal (1 546,14)."""
    return f'{float(x):,.{d}f}'.replace(',',' ').replace('.',',')


def palabra(n):return NUMEROS.get(n,str(n))


def rango(semillas):
    s=sorted(semillas)
    return f'{s[0]}-{s[-1]}' if s==list(range(s[0],s[-1]+1)) else ', '.join(map(str,s))


def incluye_cero(x):return x['ic95_inf']<=0<=x['ic95_sup']


def afirmaciones_falsas(r):
    """Afirmaciones cualitativas del texto que los resultados ya no sostienen."""
    val={x['metrica']:x for x in r['validacion']};dif={(x['escenario'],x['metrica']):x for x in r['diferencias']}
    res={(x['escenario'],x['politica'],x['metrica']):x['media'] for x in r['resumen']}
    reglas=[
        ('La atención ≤ 120 s mejora en la condición normal (IC sobre cero)',dif['normal','sla_pct']['ic95_inf']>0),
        ('El IC del abandono incluye cero en la condición normal',incluye_cero(dif['normal','abandono_pct'])),
        ('El IC de la espera total incluye cero en la condición normal',incluye_cero(dif['normal','espera_media_s'])),
        ('La espera de atendidas baja en la condición normal (IC bajo cero)',dif['normal','espera_atendidas_s']['ic95_sup']<0),
        ('Con demanda -20% el cambio de atención no es detectable',incluye_cero(dif['demanda_80','sla_pct'])),
        ('Con demanda -20% el abandono aumenta (IC sobre cero)',dif['demanda_80','abandono_pct']['ic95_inf']>0),
        ('Con demanda -20% la espera total sube (IC sobre cero)',dif['demanda_80','espera_media_s']['ic95_inf']>0),
        *[(f'La atención mejora en {e} (IC sobre cero)',dif[e,'sla_pct']['ic95_inf']>0) for e in ['demanda_120','demanda_140','servicio_115']],
        ('Con demanda +40% la mejora supera a la de la condición normal',dif['demanda_140','sla_pct']['media']>dif['normal','sla_pct']['media']),
        *[(f'Con demanda +40% la política {pol} rinde peor que en la condición normal',res['demanda_140',pol,'sla_pct']<res['normal',pol,'sla_pct']) for pol in ['base','mejorada']],
        ('La base sobreestima la atención oportuna',val['sla_pct']['simulacion_base']>val['sla_pct']['referencia_diciembre']),
        ('La base subestima la espera total',val['espera_media_s']['simulacion_base']<val['espera_media_s']['referencia_diciembre']),
        ('La base subestima el abandono',val['abandono_pct']['simulacion_base']<val['abandono_pct']['referencia_diciembre']),
    ]
    return [texto for texto,cumple in reglas if not cumple]


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resultados',default='resultados',help='carpeta de la corrida; relativa a la raíz del repositorio')
    ap.add_argument('--salida',default='output/word/informe_call_center.docx',help='DOCX a generar; relativo a la raíz')
    a=ap.parse_args(argv)
    carpeta=Path(a.resultados) if Path(a.resultados).is_absolute() else ROOT/a.resultados
    destino=Path(a.salida) if Path(a.salida).is_absolute() else ROOT/a.salida
    info=verificar_resultados(carpeta)
    falsas=afirmaciones_falsas(info['resumen'])
    if falsas:
        raise SystemExit('Los resultados contradicen afirmaciones del informe; revisar el texto antes de generarlo:\n- '+'\n- '.join(falsas))
    if carpeta.resolve()!=(ROOT/'resultados').resolve():
        print('Aviso: las figuras se toman de figuras/, generadas por figuras.py a partir de resultados/.',file=sys.stderr)
    def load(n):return json.loads((carpeta/n).read_text(encoding='utf-8'))
    def rows(n):
        with (carpeta/n).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    word=InformeWord();r=info['resumen'];p=r['parametros'];eq=json.loads((ROOT/'equipo.json').read_text(encoding='utf-8'))
    man=info['manifiesto'];opt=load('optimizacion.json')
    proc=json.loads((ROOT/'datos/procedencia.json').read_text(encoding='utf-8'))
    val={x['metrica']:x for x in r['validacion']};dif={(x['escenario'],x['metrica']):x for x in r['diferencias']}
    res={(x['escenario'],x['politica'],x['metrica']):x for x in r['resumen']}
    rep=info['repeticiones'];dias=r['dias_diciembre'];horas=sum(p['dotacion_base'])
    disp=sorted(float(x['disponibilidad']) for x in rows('calibracion.csv'))
    n_bus=len(man['semillas_busqueda']);n_rein=len(man['semillas_optimizador']);iters=man['iteraciones']
    def ic(x):return f'{fmt(x["ic95_inf"])} a {fmt(x["ic95_sup"])}'
    para=word.para
    def h(t):para(t,'Titulo2')
    def sub(t):para(t,'Sub')
    def page():pass
    table=word.tabla
    def fig(nombre,caption):word.figura(ROOT/f'figuras/{nombre}.png',caption)
    def bullet(t):para('• '+t)
    word.portada(eq)
    h('Resumen')
    para('Este informe estudia la redistribución de capacidad en un call-center bancario mediante simulación de eventos discretos y recocido simulado. Se utilizan datos públicos del banco anónimo de Technion, correspondientes a noviembre y diciembre de 1999. El objetivo es mejorar la atención dentro de un umbral de 120 segundos manteniendo la capacidad nominal diaria.')
    d=dif['normal','sla_pct'];v=val['sla_pct']
    para(f'Con {sum(p["dotacion_base"])} horas-agente programadas, la proporción atendida antes de 120 segundos pasa de <b>{fmt(v["simulacion_base"])}% a {fmt(v["simulacion_mejorada"])}%</b>. El cambio es {fmt(d["media"])} puntos porcentuales (IC 95%: {fmt(d["ic95_inf"])} a {fmt(d["ic95_sup"])}), bajo las condiciones simuladas.')
    para('La mejora es limitada: la espera media de todas las solicitudes no disminuye de forma detectable y la validación externa muestra error relevante. Se recomienda obtener registros de dotación y disponibilidad antes de implementar el horario. No se ha observado una mejora real en el banco.')
    page();h('1. Problema, objetivo y alcance')
    para('Un call-center recibe solicitudes cuya intensidad cambia durante el día. Si la capacidad disponible no acompaña ese patrón, algunas personas esperan o abandonan antes de recibir atención. El problema estudiado consiste en redistribuir una capacidad diaria fija entre 17 franjas de una hora.')
    sub('Pregunta de investigación')
    para('¿Puede una redistribución de capacidad encontrada mediante recocido simulado aumentar la proporción de solicitudes atendidas en un máximo de 120 segundos, manteniendo el presupuesto de horas-agente y los límites por franja?')
    table([['Métrica','Definición y unidad','Sentido'],
        ['Atención ≤ 120 s (principal)','100 × solicitudes atendidas con espera ≤ 120 s / todas las solicitudes que piden agente. Los abandonos cuentan como incumplimiento.','Maximizar'],
        ['Espera media total','Media de segundos hasta inicio de atención o abandono, incluyendo solicitudes con espera cero.','Minimizar'],
        ['Abandono','100 × abandonos en cola / solicitudes de agente.','Minimizar'],
        ['Espera de atendidas','Media de segundos de espera solo entre quienes reciben atención. Puede cambiar por selección de quién es atendido.','Minimizar'],
        ['P90 y tiempo extra','Percentil 90 de espera (s) y minutos desde 24:00 hasta terminar el último servicio.','Describir']],[3.9*cm,10.3*cm,3*cm])
    para('El umbral de 120 segundos es una decisión de diseño para este estudio, no un compromiso contractual documentado del banco. Cada réplica produce una métrica diaria; se reporta la media no ponderada entre réplicas. La referencia real también promedia métricas diarias.')
    sub('Límites del sistema')
    para('Se modelan domingos a jueves de 07:00 a 24:00, servicios PS (operación regular), NE (bolsa) y NW (clientes potenciales), agrupados en un pool de agentes. Se excluyen internet, atención en inglés, devoluciones de llamada, fines de semana, vacaciones, descansos individuales, reintentos, transferencias y decisiones comerciales. No se pretende describir un call-center guatemalteco actual.')
    para('Los actores son quienes llaman, los agentes y quien asigna capacidad. Las entradas son tiempos de llegada, tipo de servicio, paciencia, prioridad y capacidad horaria. Las salidas son atención, abandono, esperas y utilización. La intervención cambia únicamente la capacidad por franja; conserva las demás reglas.')
    page();h('2. Fuente, tratamiento y trazabilidad')
    para('La fuente es el archivo público de Guedj y Mandelbaum, alojado por Technion [1]. Se descargaron los meses de noviembre y diciembre de 1999 y se verificaron sus hashes SHA-256. Los registros contienen tiempos de llamadas y estados de atención. La documentación distingue servicio, abandono y llamadas PHANTOM.')
    meses={'NovemberTxt.ZIP':('Noviembre 1999','Ajuste y búsqueda'),'DecemberTxt.ZIP':('Diciembre 1999','Evaluación y validación')}
    arch=proc['archivos']
    table([['Período','Registros originales','Incluidos','Días laborales','Uso']]+
        [[meses[a['archivo']][0],fmt(a['registros_originales'],0),fmt(a['registros_incluidos'],0),str(a['dias']),meses[a['archivo']][1]] for a in arch]+
        [['Total',fmt(sum(a['registros_originales'] for a in arch),0),fmt(sum(a['registros_incluidos'] for a in arch),0),str(sum(a['dias'] for a in arch)),'Separación temporal']],[3.2*cm,3.5*cm,2.5*cm,3*cm,5*cm])
    para('Se filtran días y tipos de servicio, se descartan PHANTOM y solicitudes fuera de 07:00-24:00, y se exigen esperas no negativas y duración positiva cuando hubo servicio. La auditoría de cada filtro está en datos/procedencia.json. Los campos customer_id, call_id, vru+line y server se eliminan antes de guardar los CSV utilizados por el proyecto.')
    table([['Naturaleza','Elementos'],['Datos reales observados','Fecha, llegada desde la VRU, tipo, espera, duración de servicio, resultado y prioridad registrada.'],['Estimaciones','Tasas horarias, mezcla de tipos, momentos del servicio, paciencia media, capacidad inferida y disponibilidad efectiva.'],['Supuestos de diseño','Pool compartido, paciencia exponencial, umbral 120 s, cambio máximo ±2 agentes por hora y capacidad 1-9.'],['Datos sintéticos','Días generados para buscar la solución, servicios y paciencia sorteados, variaciones de demanda y duración.']],[4.3*cm,12.9*cm])
    para('La documentación de la fuente permite uso gratuito, solicita reconocer a sus autores y notificar el uso a Avi Mandelbaum [1]. Se incluye una nota para realizar esa notificación; no se ha enviado automáticamente. Los archivos ZIP originales no forman parte del paquete de entrega. El script puede descargarlos, verificar sus hashes y reconstruir los datos sin identificadores.')
    sub('Separación de los datos')
    para('Noviembre determina todos los parámetros y la solución elegida. En diciembre se toman únicamente fechas, llegadas y tipos como entradas del replay; sus esperas y resultados se reservan para validación. Los escenarios de sensibilidad son perturbaciones sintéticas de los días de diciembre. Se mantuvo fija la solución durante toda la evaluación.')
    page();h('3. Modelo y simulación de eventos discretos')
    para('Llegadas → Cola con prioridad → Agentes → Atención','Formula').paragraph_format.keep_with_next=True
    para('Desde la cola: abandono al agotar la paciencia.','Formula').paragraph_format.keep_with_next=True
    para('Figura 1. Relación entre las entradas, la cola, la capacidad de atención y las salidas.','Peq')
    table([['Variable','Interpretación','Unidad'],['t, A_i, S_i, P_i','Reloj, llegada, servicio observado modelado y paciencia','segundos'],['Q(t), B(t), c_h','Solicitudes en cola, agentes ocupados y capacidad de la hora h','conteos'],['estado_i','Futura, cola, servicio, terminada o abandono','categoría'],['η','Disponibilidad efectiva; duración de ocupación = S_i / η','fracción'],['W_i','Tiempo desde solicitud de agente hasta atención o abandono','segundos']],[3.5*cm,10.9*cm,2.8*cm])
    para('La agenda contiene llegadas, finalizaciones, cambios de capacidad y vencimientos de paciencia. Se usa un heap para extraer el siguiente evento [6]. La cola ordena por llegada virtual A_i - 90 I(prioritaria). No hay interrupción del servicio. Al bajar c_h, los agentes ocupados terminan su llamada y no se admiten nuevos servicios hasta que B(t) &lt; c_h.')
    para('En empates, se procesan finalizaciones antes que cambios de capacidad, llegadas y abandonos. Una plaza que queda libre exactamente al vencer la paciencia permite atender. A las 24:00 cesan las llegadas; se mantiene la última capacidad para vaciar la cola y terminar los servicios. El tiempo extra se reporta por separado.')
    para('Se verifica en cada ejecución que N = atendidas + abandonadas y que el área total bajo Q(t), incluido el vaciado posterior al cierre, coincide con la suma de todas las esperas. Esta área se guarda como area_cola_s, en llamada-segundos. La métrica cola_media integra Q(t) únicamente entre 07:00 y 24:00 y divide entre 61 200 segundos; representa el promedio de solicitudes en cola durante la apertura. Se inicia cada jornada sin cola ni servicios en curso; esa condición de apertura es un supuesto.')
    para('El código del motor, el manejo de eventos y la política de asignación son propios de este proyecto. NumPy genera variables aleatorias y administra semillas; heapq aporta la estructura de prioridad. No se delegó la simulación ni el optimizador a una función de biblioteca.')
    page();h('4. Parámetros y calibración')
    para('El análisis empírico de Brown et al. separa llegadas, servicio y paciencia como componentes de la operación y estudia aproximaciones lognormales del servicio [2]. Aquí se ajusta una lognormal por tipo mediante momentos: σ² = ln(1 + v/m²), μ = ln(m) - σ²/2. No se afirma que esta distribución sea exacta.')
    table([['Tipo','Media de servicio (s)','Desv. estándar (s)','n atendidas']]+[[k,fmt(v['media_s']),fmt(v['sd_s']),v['n']] for k,v in p['servicio'].items()],[3.3*cm,4.7*cm,5.2*cm,4*cm])
    para(f'La paciencia exponencial usa una media estimada de {fmt(p["paciencia_media_s"])} s. Su estimador es la exposición total en cola dividida entre el número de abandonos. Las esperas de quienes son atendidos son observaciones censuradas por la derecha; promediar solo las esperas de los abandonos ignoraría esa información. Se supone independencia entre paciencia y servicio.')
    para(f'La proporción prioritaria se estima entre llamadas que sí esperaron: {fmt(100*p["fraccion_prioritaria"],1)}%. La documentación reporta un problema de registro de prioridad en quienes no esperan [1]. La asignación aleatoria de prioridad es una aproximación; no reconstruye la categoría real de cada persona.')
    para('Para buscar el horario se simula una intensidad constante dentro de cada hora y variable entre horas. Un factor Gamma diario de media uno reproduce parte de la variabilidad entre jornadas. Condicional a ese factor, el número de llegadas en cada hora es Poisson y sus instantes se distribuyen uniformemente dentro de la hora. Esta mezcla conserva variabilidad entre días y no equivale a afirmar que todas las llegadas reales son Poisson.')
    sub('Capacidad y disponibilidad efectiva')
    para(f'Para cada día y hora de noviembre se calcula el pico de servicios simultáneos. Se promedian estos picos, se redondean y se limita la capacidad a 1-9 puestos; la suma base es {horas} horas-agente. Es un proxy de capacidad, no una nómina ni un horario observado. La disponibilidad η = {fmt(p["disponibilidad"],3)} se calibra en una malla {fmt(disp[0],3)}-{fmt(disp[-1],3)} con pasos de {fmt(disp[1]-disp[0],3)} y {len(man["semillas_calibracion"])} réplicas.')
    para('Se minimiza la suma de errores cuadrados escalados de espera media (escala 10 s), abandono (5 pp) y atención ≤ 120 s (5 pp), usando solo noviembre. η representa demoras de ocupación no modeladas y errores de agregación; no prueba que el banco tenga esa productividad. Las escalas son elecciones de calibración documentadas en experimentos.py.')
    page();h('5. Técnica adicional: recocido simulado')
    para('El recocido simulado propone modificaciones de una solución y acepta ocasionalmente un aumento de costo con probabilidad exp(-Δ/T). La temperatura T disminuye y reduce esa tolerancia [3]. Se implementa una versión discreta propia; la documentación de Dual Annealing de SciPy se usa como contraste de diseño, no como el algoritmo ejecutado [4].')
    para('La solución es el vector entero c = (c_7, …, c_23). Un vecino traslada una hora-agente de una franja a otra, sin cambiar el presupuesto. Este movimiento hace factible cada candidato por construcción y una comprobación explícita vuelve a verificarlo.')
    para('min J(c) = promedio de [100 - atención ≤ 120 s (%)]','Formula')
    para(f'Σ c_h = {horas}; max(1, b_h - 2) ≤ c_h ≤ min(9, b_h + 2); c_h entero','Formula')
    para('b_h es la capacidad base. Los límites ±2 evitan concentrar todo el costo de la mejora en una sola franja, aunque no garantizan equidad individual ni un nivel de servicio por hora. Una exploración inicial sin este límite produjo concentraciones poco defendibles; se añadió la restricción a partir de esa observación de entrenamiento y se regeneraron los resultados finales.')
    table([['Parámetro','Valor','Motivo'],['Temperatura inicial / final',f'{fmt(opt["temperatura_inicial"])} / {fmt(opt["temperatura_final"])} puntos de costo','Explorar al comienzo y concentrar la búsqueda al final'],['Enfriamiento',f'Geométrico en {iters} iteraciones','Presupuesto computacional reproducible'],['Reinicios',f'{n_rein}: semillas {", ".join(map(str,man["semillas_optimizador"]))}','Examinar sensibilidad a la trayectoria de búsqueda'],['Entradas de búsqueda',f'{n_bus} días sintéticos, semillas {rango(man["semillas_busqueda"])}','Comparar candidatos con números aleatorios comunes'],['Selección','Menor costo de entrenamiento','No elegir con resultados de diciembre']],[5*cm,5.3*cm,6.9*cm])
    para(f'Pseudocódigo: iniciar en la base; proponer un traslado factible; simular sobre las mismas {palabra(n_bus)} entradas; aceptar si mejora o con exp(-Δ/T); conservar la mejor solución; enfriar; terminar después de {iters} pasos. Se almacenan costos, temperaturas, aceptaciones y movimientos.')
    para(f'La búsqueda exhaustiva crece demasiado para 17 variables enteras; un método voraz puede quedar atrapado en óptimos locales. Un algoritmo genético requeriría diseñar cruce y reparación para conservar horas. El recocido permite controlar esas restricciones directamente. No garantiza el óptimo global y puede sobreajustarse a {palabra(n_bus)} días simulados o a la temperatura elegida. Por eso la evaluación usa entradas y semillas nuevas.')
    para('El optimizador exige al menos una entrada de ajuste. Si la capacidad inicial no permite ningún traslado factible, devuelve la base y registra esa causa de terminación. Los generadores rechazan semillas inválidas y factores no finitos; el motor también valida disponibilidad y umbral de atención antes de simular.')
    page();h('6. Diseño experimental y reproducibilidad')
    cada=f'Base y propuesta / {rep} cada una'
    table([['Condición','Llegadas','Duración de servicio','Políticas / réplicas'],['Normal','Replay de diciembre','Modelo ajustado con noviembre',cada],['Demanda -20%','Thinning al 80%','Sin cambio',cada],['Demanda +20%','Superposición bootstrap al 120%','Sin cambio',cada],['Demanda +40%','Superposición bootstrap al 140%','Sin cambio',cada],['Servicio +15%','Replay normal','Duraciones × 1,15',cada]],[3.4*cm,5.4*cm,4*cm,4.4*cm])
    para(f'Se ejecutaron {info["corridas"]} comparaciones individuales: {palabra(info["condiciones"])} condiciones × {palabra(info["politicas"])} políticas × {rep} réplicas. Cada semilla sortea uniformemente uno de los {dias} días de diciembre, conserva sus llegadas y tipos en la condición normal, y genera servicio, paciencia y prioridad. Las réplicas usan semillas distintas y son independientes respecto de la aleatoriedad computacional. Los {dias} días de referencia son fijos; no equivalen a {rep} días reales nuevos.')
    para('Dentro de cada pareja base-propuesta se reutiliza la misma lista inmutable de llamadas. Para una diferencia D_r se reporta media ± t(0,975; R-1) × s(D)/√R. Los IC son marginales del 95%; no son bandas simultáneas para todas las métricas y sensibilidades. La métrica primaria se fijó antes de evaluar.')
    table([['Etapa','Semillas'],['Calibración',rango(man['semillas_calibracion'])],['Búsqueda: entradas / algoritmo',f'{rango(man["semillas_busqueda"])} / {", ".join(map(str,man["semillas_optimizador"]))}'],['Evaluación final',rango(info['semillas'])],['Validación por día',f'200000 + 30 × índice de día + repetición; 30 por cada uno de {dias} días']],[6*cm,11.2*cm])
    para(f'La validación adicional simula cada día de diciembre 30 veces con sus propias llegadas y compara su promedio con el registro real del mismo día. Esa comparación evita confundir el error del modelo con la composición aleatoria de días elegida en las {rep} réplicas principales.')
    para('Los generadores usan PCG64 mediante NumPy y SeedSequence para separar subflujos [5]. resultados/manifiesto.json registra el estado de la corrida, su configuración, semillas, versiones, el commit del código, hashes de los datos y tiempo de ejecución. La reproducibilidad exacta debe verificarse con las versiones probadas, pues las distribuciones de alto nivel pueden variar entre versiones de bibliotecas.')
    para('Cada corrida se escribe primero en una carpeta terminada en .en_curso. Solo al finalizar se publica en el directorio de salida y la evidencia anterior se conserva en una carpeta .anterior. El argumento --salida permite separar experimentos. El verificador comprueba el estado completo, las semillas, el número de réplicas declarado y la coherencia entre corridas y diferencias pareadas antes de generar el informe.')
    page();h('7. Resultados de la comparación')
    fig('02_comparacion_real',f'Figura 2. Medias diarias de la referencia real de diciembre y de las {rep} réplicas de cada política. Los abandonos se incluyen en el denominador del umbral de atención.')
    labels={'sla_pct':'Atendidas ≤ 120 s (%)','abandono_pct':'Abandono (%)','espera_media_s':'Espera total (s)','espera_atendidas_s':'Espera atendidas (s)','p90_espera_s':'P90 espera (s)'}
    table([['Métrica','Real','Base','Propuesta','Δ propuesta-base']]+[[labels[m],fmt(val[m]['referencia_diciembre']),fmt(val[m]['simulacion_base']),fmt(val[m]['simulacion_mejorada']),fmt(val[m]['cambio_absoluto'])] for m in labels],[5.6*cm,2.6*cm,2.6*cm,2.8*cm,3.6*cm])
    para(f'Los cambios de porcentajes en la última columna se expresan en puntos porcentuales; los demás conservan segundos. La mejora relativa del indicador principal es {fmt(val["sla_pct"]["cambio_relativo_pct"])}%, diferente de su cambio absoluto de {fmt(val["sla_pct"]["cambio_absoluto"])} pp.')
    fig('03_incertidumbre','Figura 3. Intervalos pareados del 95%. Atención ≤ 120 s mejora; los intervalos de abandono y espera total incluyen cero. No se concluye equivalencia exacta.')
    ea=val['espera_atendidas_s']
    para(f'La espera media entre quienes son atendidos baja {fmt(-ea["cambio_absoluto"])} s ({fmt(-ea["cambio_relativo_pct"])}%). Esta métrica condicionada no debe confundirse con la espera de todas las solicitudes. El aumento del indicador principal no demuestra una reducción general de la cola ni del abandono.')
    page();h('8. Validación frente a la referencia real')
    table([['Métrica','Error absoluto base','Error relativo','MAE diario'],['Atendidas ≤ 120 s',fmt(val['sla_pct']['error_absoluto_base'])+' pp',fmt(val['sla_pct']['error_relativo_base_pct'])+'%',fmt(r['mae_diario']['sla_pct'])+' pp'],['Abandono',fmt(val['abandono_pct']['error_absoluto_base'])+' pp',fmt(val['abandono_pct']['error_relativo_base_pct'])+'%',fmt(r['mae_diario']['abandono_pct'])+' pp'],['Espera total',fmt(val['espera_media_s']['error_absoluto_base'])+' s',fmt(val['espera_media_s']['error_relativo_base_pct'])+'%',fmt(r['mae_diario']['espera_media_s'])+' s']],[5.4*cm,4*cm,3.6*cm,4.2*cm])
    ve=val['espera_media_s']
    para(f'La base sobreestima la atención oportuna y subestima espera y abandono. El error medio de espera es {fmt(ve["error_absoluto_base"])} s ({fmt(ve["error_relativo_base_pct"])}%). El MAE por día asciende a {fmt(r["mae_diario"]["espera_media_s"])} s. Por tanto, la correspondencia con el referente real es parcial y no justifica interpretar la mejora del simulador como una predicción operativa validada.')
    fig('05_validacion_diaria','Figura 4. Cada punto representa un día de diciembre. La diagonal es igualdad con el dato real; la dispersión y el sesgo muestran límites de la representación.')
    para(f'La referencia real media contiene {fmt(val["llamadas"]["referencia_diciembre"])} solicitudes por día. Las {rep} réplicas seleccionaron días con una media de {fmt(val["llamadas"]["simulacion_base"],0)} solicitudes: el sorteo de días no pondera exactamente igual todos los registros en una muestra finita. La validación por día compara las mismas llegadas y reporta el error que permanece después de controlar esa diferencia.')
    para('Entre las explicaciones plausibles están cambios del servicio entre meses, interrupciones no observadas, heterogeneidad entre agentes y horarios desconocidos. Estas son hipótesis de modelización, no causas verificadas. La calibración de un único factor de disponibilidad no elimina la necesidad de medir esos componentes.')
    page();h('9. Sensibilidad y comportamiento del sistema')
    fig('04_sensibilidad','Figura 5. Se conserva el horario propuesto; no se vuelve a optimizar para cada demanda. Las barras representan IC del 95% entre réplicas.')
    esc=[('demanda_80','Demanda -20%'),('normal','Normal'),('demanda_120','Demanda +20%'),('demanda_140','Demanda +40%'),('servicio_115','Servicio +15%')]
    table([['Condición','Atención base (%)','Propuesta (%)','Δ (pp)','IC 95% Δ (pp)']]+[[label,fmt(res[e,'base','sla_pct']['media']),fmt(res[e,'mejorada','sla_pct']['media']),fmt(dif[e,'sla_pct']['media']),f"[{fmt(dif[e,'sla_pct']['ic95_inf'])}; {fmt(dif[e,'sla_pct']['ic95_sup'])}]"] for e,label in esc],[4.2*cm,3.4*cm,3.3*cm,2.1*cm,4.2*cm])
    ab=dif['demanda_80','abandono_pct']
    para(f'Con 20% menos demanda, el cambio del indicador principal no es detectable y el abandono aumenta {fmt(ab["media"])} pp (IC 95%: {ic(ab)}). La espera total sube {fmt(dif["demanda_80","espera_media_s"]["media"])} s. La intervención no domina a la base en todas las condiciones.')
    para(f'Con 40% más demanda, el indicador mejora aproximadamente {fmt(dif["demanda_140","sla_pct"]["media"])} pp, pero ambas políticas tienen peor desempeño absoluto que en la condición normal. Redistribuir un presupuesto fijo no reemplaza añadir capacidad cuando el sistema está sobrecargado. Un beneficio mayor que en la condición normal no implica que el servicio sea suficiente.')
    page();h('10. Horario candidato y trayectoria')
    fig('01_demanda_y_capacidad','Figura 6. Demanda observada y capacidad. Cada escalón ocupa una hora completa, desde las 07:00 hasta las 24:00. La base es una inferencia de actividad; la propuesta respeta el mismo presupuesto y los límites locales.')
    table([['Hora']+[str(i) for i in range(7,16)],['Base']+[str(x) for x in p['dotacion_base'][:9]],['Propuesta']+[str(x) for x in r['dotacion_mejorada'][:9]]] , [2.8*cm]+[1.6*cm]*9)
    table([['Hora']+[str(i) for i in range(16,24)],['Base']+[str(x) for x in p['dotacion_base'][9:]],['Propuesta']+[str(x) for x in r['dotacion_mejorada'][9:]]] , [2.8*cm]+[1.8*cm]*8)
    para(f'Estos números especifican capacidad horaria agregada. No asignan personas, turnos, descansos ni contratos. Al terminar servicios después de un cambio de hora puede existir ocupación transitoria superior a la nueva capacidad; se impide iniciar más servicios hasta liberarla. El presupuesto de {horas} horas es nominal, y el vaciado puede producir tiempo extra.')
    page();h('11. Búsqueda y demostración')
    fig('06_busqueda',f'Figura 7. {palabra(n_rein).capitalize()} reinicios del recocido simulado. La trayectoria conserva el mejor costo de entrenamiento; las soluciones son candidatas, no óptimos certificados.')
    fig('07_trayectoria','Figura 8. Evolución de cola y ocupación en una réplica. Un solo recorrido sirve para explicar el mecanismo; las conclusiones usan el conjunto de experimentos.')
    para(f'La demo ejecuta el mismo motor de los experimentos. Permite modificar demanda, duración del servicio y semilla; muestra ambas políticas y exporta la réplica en JSON. El panel de evidencia mantiene los resultados guardados para distinguir una ejecución ilustrativa de las {rep} réplicas del estudio.')
    page();h('12. Verificación y ejecución')
    para('Las pruebas automatizadas cubren casos manuales de atención y abandono, orden de prioridades, empates al vencer paciencia, disminución y aumento de capacidad, vaciado al cierre, capacidad suficiente, entradas inválidas, presupuesto del optimizador, terminación sin movimientos factibles, determinismo, corridas aisladas y coherencia de la evidencia guardada. También comprueban la separación entre cola de apertura y área total, y los límites horarios de las gráficas. Además, cada simulación comprueba conservación de solicitudes y la identidad entre área de cola y suma de esperas.')
    para('Las pruebas de entrega verifican conjuntos consistentes con distintos números de réplicas, rechazan resultados incompletos o mezclados y detectan cifras desactualizadas en la documentación. Las pruebas HTTP comprueban la página, la evidencia y la simulación, además de respuestas ante entradas inválidas, archivos ausentes o dañados y recuperación después de un error. La demo reproduce las métricas y la traza de la réplica guardada.')
    table([['Archivo o carpeta','Responsabilidad'],['src/modelo.py','Generadores, eventos discretos y métricas'],['src/ajuste.py / src/optimizacion.py','Estimación exclusiva de noviembre / recocido y restricciones'],['scripts/preparar_datos.py','Descarga, hashes, filtros y eliminación de identificadores'],['experimentos.py / resultados/','Diseño, semillas, tablas, validación y evidencia'],['app.py / web/index.html','Servidor local e interfaz de la demo'],['figuras.py / informe.py','Regeneración de figuras y del informe'],['tests/ / scripts/verificar_entrega.py','Pruebas del modelo, la aplicación y la coherencia de la entrega']],[6.3*cm,10.9*cm])
    sub('Entorno limpio')
    for linea in ['python3 -m venv .venv','source .venv/bin/activate','python -m pip install -r requirements-lock.txt','python -m unittest discover -s tests -v','python scripts/verificar_entrega.py','python app.py']:
        para(escape(linea),'Formula')
    para('Abrir http://127.0.0.1:8765. En Windows con PowerShell, crear el entorno con py -3.11 -m venv .venv y activar con .venv\\Scripts\\Activate.ps1. Si no se permite la activación, usar .venv\\Scripts\\python.exe directamente. El README contiene las instrucciones por sistema operativo. La demo admite --port para elegir otro puerto y --resultados para cargar una corrida distinta.')
    para('Para reconstruir la evidencia de esta entrega, ejecutar python experimentos.py --repeticiones 60 --iteraciones 400, seguido de python figuras.py y python informe.py. El último comando genera el Word; se requiere Times New Roman instalada para exportarlo a PDF desde Word o LibreOffice con el formato previsto. El verificador y el informe aceptan --resultados para leer otra carpeta; las figuras deben corresponder a esa misma corrida. Para volver a descargar los datos: python scripts/preparar_datos.py. Los CSV depurados permiten revisar la evidencia y ejecutar la demo sin descargar de nuevo los registros originales.')
    para('requirements-lock.txt fija las dependencias directas y transitivas para Python 3.9 a 3.12; el README documenta la instalación y comprobación en Windows y macOS. El informe se genera a partir de resultados verificados y la generación se detiene cuando estos contradicen las conclusiones cualitativas del texto. El código separa simulación, ajuste, optimización, visualización y entrega. La documentación incluye un guion de 15 minutos con demostración y preguntas.')
    page();h('13. Discusión, conclusión y recomendación')
    para(f'<b>Qué mejoró y cuánto.</b> El indicador principal mejora {fmt(dif["normal","sla_pct"]["media"])} pp en la distribución de días de diciembre simulada, con presupuesto nominal constante. La espera de atendidas disminuye {fmt(-ea["cambio_absoluto"])} s. No hay evidencia de reducción del abandono ni de la espera total en la condición normal.')
    para(f'<b>Bajo qué condiciones.</b> El resultado corresponde al pool PS/NE/NW, horarios laborales locales, disponibilidad calibrada de {fmt(p["disponibilidad"],3)} y límites de redistribución ±2. La mejora del indicador se mantiene con mayor demanda y servicios más largos, pero no se detecta con 20% menos demanda y allí empeora el abandono.')
    para(f'<b>Qué tan confiable es la comparación.</b> Las parejas comparten entradas y tienen {rep} semillas independientes por condición, con separación temporal entre ajuste y validación. El IC pareado apoya una mejora dentro del simulador. El error de validación es mayor que el efecto de la intervención en varias métricas y limita cualquier inferencia sobre la realidad.')
    sub('Limitaciones que permanecen')
    for t in ['La dotación es inferida; no se dispone de horarios contractuales, pausas ni tiempo de trabajo auxiliar. La disponibilidad calibrada puede absorber errores estructurales.',
              'La independencia entre paciencia, servicio y prioridad es supuesta. La paciencia exponencial y el pool único omiten comportamiento y habilidades heterogéneas.',
              'Noviembre y diciembre pueden tener patrones diferentes. Los datos de 1999 no describen tecnologías ni demandas actuales.',
              f'La búsqueda considera {palabra(n_bus)} días sintéticos y {palabra(n_rein)} reinicios, sin garantía de optimalidad. Los IC no incorporan incertidumbre de parámetros, selección del modelo ni toda la variación entre meses.',
              'El objetivo agregado permite compensar pérdidas entre horas. El límite ±2 reduce extremos, pero no asegura equidad por tipo o franja.',
              'No se ha implementado la propuesta en un call-center real; las mejoras son contrafactuales simulados.']:
        bullet(t)
    para('<b>Conclusión.</b> Es posible mejorar de forma medible una métrica de atención en este modelo con la misma capacidad nominal. La mejora es pequeña y no generaliza a todas las métricas ni condiciones. El proyecto demuestra una metodología reproducible para buscar y contrastar una intervención, junto con sus límites.')
    para('<b>Recomendación.</b> Mantener la propuesta como candidata de análisis. Obtener registros reales de disponibilidad y calibrar por hora y tipo; después repetir una evaluación temporal con parámetros congelados y objetivos de servicio por franja. Solo tras esa validación tendría sentido diseñar turnos individuales y un piloto medido.')
    page();h('14. Referencias y contribuciones')
    refs=[('[1] Guedj, I., y Mandelbaum, A. (2000). Anonymous Bank Call-Center Data. Documentación del 9 de febrero de 2000 y archivos de 1999. Technion.','https://serveng.technion.ac.il/homeworks/call-center-data/'),
        ('[2] Brown, L., Gans, N., Mandelbaum, A., Sakov, A., Shen, H., Zeltyn, S., y Zhao, L. (2005). Statistical Analysis of a Telephone Call Center: A Queueing-Science Perspective. JASA, 100(469), 36-50. Versión de autor de 2004 consultada.','https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Statistical-analysis2.pdf'),
        ('[3] Kirkpatrick, S., Gelatt, C. D., y Vecchi, M. P. (1983). Optimization by Simulated Annealing. Science, 220(4598), 671-680. DOI: 10.1126/science.220.4598.671.','https://hedibert.org/wp-content/uploads/2013/12/1983KirkpatrickGelattVecchi.pdf'),
        ('[4] SciPy Developers. dual_annealing: documentación técnica. Referencia comparativa; esta función no se invoca en el proyecto.','https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html'),
        ('[5] NumPy Developers. PCG64 y SeedSequence: documentación técnica de generación reproducible.','https://numpy.org/doc/stable/reference/random/bit_generators/pcg64.html'),
        ('[6] Python Software Foundation. heapq: documentación de colas de prioridad.','https://docs.python.org/3/library/heapq.html')]
    for texto,url in refs:para(escape(texto)+'<br/><link href="'+url+'">Consultar fuente en línea</link>','Peq')
    para('Consulta de fuentes públicas: 8 de noviembre de 2026. También se utilizaron pandas para procesar registros, Matplotlib para gráficas, SciPy para cuantiles t y python-docx para el informe en Word. El PDF se exportó desde el DOCX con Microsoft Word.','Peq')
    sub('Registro de contribuciones')
    table([['Integrante','Registro de aportes']]+[[x['nombre'],x['aporte_confirmado']] for x in eq['integrantes']],[5.1*cm,12.1*cm])
    para('El archivo docs/CONTRIBUCIONES.md permite registrar tareas realizadas, evidencia y revisión de cada integrante. El reparto del guion de exposición es una propuesta para ensayar.')
    word.guardar(destino)
    print(destino)


if __name__=='__main__':main()
