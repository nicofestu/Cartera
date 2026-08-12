# Cartera — principios de diseño y contexto operativo

Documento único. Se lee **antes** de proponer o implementar cualquier cambio.
Reemplaza a `PRINCIPIOS.md` y `PROYECTO_CARTERA_CONTEXTO_E_INSTRUCCIONES.md`
como archivos separados: este es el único.

Última revisión: 2026-08-12 (madrugada) — Nicolás detectó que la card
"Retorno total" y el gráfico "Rendimiento acumulado" de Histórico
completo/YTD mostraban dos números distintos para lo mismo (+24% en la
card vs. +15% en el gráfico, y la cartera pasaba de ganarle a SPY a
perderle según cuál se mirara). Causa: el gráfico de esa ventana seguía
usando la fórmula money-weighted vieja (`serieRendimiento()`/`retHoy` =
(valor+retirado)/aportado−1) mientras las cards y la tabla comparativa ya
habían migrado al time-weighted encadenado (`retornoEntre` sobre
`serieDiaria()`) — un refactor que se aplicó a las cards pero no se
propagó al gráfico de esa ventana en particular (el gráfico de los demás
períodos y el mini-gráfico de Inicio sí ya usaban el motor correcto). Ver
§6 regla 14: mismo principio de fuente única que ya regía el benchmark
(§5), aplicado acá.

Última revisión: 2026-08-12 (noche, más tarde) — el usuario corrigió con
ChatGPT (commits directos a `main`, sin el pipeline de validación habitual)
un bug real de saldos declarados que cancelaba ventas contado inmediato en
el NAV y la liquidez, más un bug de interpretación de `liq` como string.
Revisado, validado (`node --check` + identificadores + smoke tests) y
encontrado un hueco residual que Claude corrigió encima: la migración de
saldos (`migrarSaldosRealesAjustes()`) solo corría al recargar la página o
sincronizar, no al guardar el modal de saldos, así que declarar un saldo y
operar en la misma sesión sin recargar seguía perdiendo la plata. Ver §6,
regla 13, para el detalle completo (causa raíz, por qué el arreglo original
no alcanzaba solo, y la lección para el hito 7+ de cartera-app).

Última revisión: 2026-08-12 (noche) — se reescribe §5 para describir la
arquitectura ACTUAL del benchmark (tres fuentes encadenadas por retorno:
CEDEAR en USD, `historial/{año}.json` como respaldo reciente, índice
oficial por empalme; más dividendos compuestos y ajuste de ratio). El
texto anterior documentaba la decisión original, más simple, que ya había
quedado atrás en el código.

Última revisión: 2026-08-12 — hito 5 (Rendimientos) en §26: se agrega
benchmark contra S&P 500 y Nasdaq 100 (`lib/cartera/benchmark.ts`, nuevo),
puerto del motor ACTUAL de Cartera legado. Con esto el núcleo financiero de
Rendimientos queda completo; lo que resta pasa a hito 7+.

Última revisión: 2026-08-12 — hito 5 (Rendimientos) en §26: se agrega TIR
(XIRR) y selector de período (`rangoPeriodo`, `retornoEntre`, `xirr`,
`tirDe`), puerto fiel del legado, con selector Hoy/Semana/Mes/YTD/1A/Todo
en `/dashboard/cartera`. Sigue en curso: falta benchmark (hito 3d).

Última revisión: 2026-08-12 — hito 5 (Rendimientos) en §26: se agrega
retorno por tramo con Modified Dietz (`serieDiaria()`), puerto fiel de
`serieDiaria()` del legado, ya mostrado en `/dashboard/cartera` junto al
retorno acumulado. Sigue en curso: falta TIR/XIRR y benchmark (hito 3d).

Última revisión: 2026-08-11 (noche) — se agrega hito nuevo en §26:
migración de `movimientos` y `snapshots` del gist legado a cartera-app, con
prioridad ALTA (antes de cerrar Rendimientos) a pedido explícito del
usuario para no perder esa historia. Se renumeran los hitos del núcleo
(ahora 1-6) y "hito 5+" pasa a llamarse "hito 7+" para no chocar.
Rendimientos (hito 5) marcado "en curso": retorno acumulado ya hecho.

Última revisión: 2026-08-11 (tarde) — hito 2 (Cauciones) marcado ✅ en
§26; se documenta el snapshot diario vía Vercel Cron Job como mejora
deliberada sobre Cartera legado (no una copia — ver §26, punto 3), y se
agrega el manejo de `SUPABASE_SERVICE_ROLE_KEY` a §24.

Última revisión: 2026-08-11 — se agrega §26: objetivo final de cartera-app
(paridad completa con Cartera) y el plan de hitos para llegar ahí. También
se sincroniza esta copia con la del repo `nicofestu/Cartera`, que había
quedado atrasada (le faltaban §0bis y §23-25).

Revisión 2026-08-10 — se agrega §0bis y §23-25: cartera-app pasa a ser el
producto multiusuario activo; Cartera queda como legado y referencia de
lógica (ver §0bis).

---

## 0. Qué es el proyecto

Aplicación web personal de seguimiento de inversiones. Repositorio público:
`nicofestu/Cartera`.

```
index.html                                la app entera (HTML + CSS + JS)
historial/2022.json … 2026.json           cierre diario de precios por especie (lo escribe un Action)
historial/indices.json                    series diarias de S&P 500 y Nasdaq 100 + calibración
scripts/snapshot_historial.py             el scraper que alimenta historial/AAAA.json
.github/workflows/snapshot-benchmarks.yml lo corre 21:30 UTC, lunes a viernes
README.md
```

- La app es un único archivo `index.html`, 100% del lado del cliente. No hay
  backend propio.
- Los **datos públicos de mercado** viven en `historial/` dentro del repo.
- Los **datos personales** viven en un gist secreto (ver §4).
- El cruce entre ambos ocurre solo en el navegador del usuario.

Funciones: NAV, posiciones, movimientos, P&L realizado y no realizado,
liquidez, múltiples cuentas, ARS / USD MEP / USD CCL, rendimientos
históricos, benchmarks contra S&P 500 y Nasdaq 100, métricas de riesgo,
importación de operaciones de brókers, datos de mercado, panel macro,
sincronización con GitHub Gist y fondo de pantalla desde la API de imágenes
de NASA.

---

## 0bis. Dos proyectos, un objetivo (desde 2026-08)

**Cartera deja de ser el destino final.** A partir de acá conviven dos
repositorios con roles distintos:

| | `nicofestu/Cartera` | `nicofestu/cartera-app` |
|---|---|---|
| Rol | **Legado / referencia de lógica.** Congelado salvo fixes puntuales. | **Producto activo.** Acá se construye la versión multiusuario. |
| Visibilidad | Público, GitHub Pages | Privado, desplegado en Vercel |
| Stack | HTML+JS embebido, sin backend, un solo archivo | Next.js + TypeScript, Supabase (auth + DB), Vercel |
| Usuarios | Uno (Nicolás), datos en gist secreto | Múltiples, cada uno con su cuenta y sus datos |
| Cambios | Se pegan a mano en el editor web de GitHub | Se commitean vía GitHub API (o el flujo que el usuario prefiera) |

**Qué significa "legado" para Cartera:** toda la lógica financiera ya
validada acá (motor de benchmark, métricas de riesgo, Modified Dietz,
manejo de cauciones, reconstrucción de NAV, etc. — ver §5 en adelante) es
la **fuente de verdad conceptual** que hay que portar a cartera-app. No se
reinventa esa lógica desde cero: se traduce, adaptándola a un modelo de
datos multiusuario (Supabase con Row Level Security en vez de un gist por
persona). Cartera sigue recibiendo correcciones si aparece un bug real,
pero no features nuevas pensadas solo para el caso de un usuario.

**Qué significa "activo" para cartera-app:** acá el criterio ya no es "que
funcione para mi cartera" ni siquiera "que funcione para cualquier
cartera calculada en un archivo suelto" — es que **funcione de forma
segura para N usuarios simultáneos que no se conocen entre sí, sin que
los datos de uno puedan verse, mezclarse ni pisarse con los de otro.**
Ver §23 para la disciplina de cambios específica de este repo.

Cuando una instrucción de este documento (pensada originalmente para
Cartera) no tenga sentido literal en cartera-app —por ejemplo, "pegar en
el editor web de GitHub"— se aplica el equivalente correcto para ese
stack, no se ignora el espíritu de la instrucción.

---

## 1. Principio rector: escalar, no adaptar

**Esta aplicación se construye para servir a cualquier cartera, no a una en
particular.** Es el criterio que gana cuando hay conflicto con otros.

*(Nota 2026-08: este principio nació pensando en generalizar la lógica de
cálculo dentro de un archivo de uso personal. Sigue vigente tal cual para
Cartera. En cartera-app se vuelve literal — "cualquier cartera" pasa a ser
"cualquier usuario, con aislamiento real de datos" — ver §23.)*

Que hoy la use una sola persona no autoriza a resolver nada "porque en este
caso alcanza". Un atajo que funciona para una cartera concreta —y solo por
las fechas, los instrumentos o los brókers que esa cartera tiene— es deuda
que se paga cuando entra la segunda.

Consecuencias operativas, todas verificables:

1. **Ningún camino de cálculo puede depender de la fecha de inicio, los
   tickers o los brókers de una cartera puntual.** Si un benchmark, una
   métrica o una reconstrucción funciona porque "esta cartera arranca
   después de tal fecha", está mal construido. Tiene que degradar con
   elegancia hacia atrás, no romperse ni mentir.
2. **Los datos históricos no se tiran.** Aunque una cartera concreta no los
   necesite, otra sí. Cuesta bytes conservarlos y cuesta años recuperarlos.
3. **Los parámetros y las series van en JSON del repo, no en el código.**
   Recalibrar o corregir no puede obligar a tocar un archivo de 300 KB.
4. **Nada calibrado a mano puede estar en un camino que produzca un
   retorno.** Ver §5.
5. **Un dato faltante se declara, no se rellena en silencio.** Preferimos no
   mostrar una card antes que mostrar un número inventado.
6. **Los datos personales viven en el gist privado.** Nunca en este repo,
   nunca en un archivo de contexto público, ni siquiera como ejemplo.

---

## 2. Perfil del usuario

No sabe programación. Por lo tanto:

- no asumir conocimientos de HTML, CSS, JavaScript, Node, Git o GitHub;
- explicar la implementación paso a paso e indicar exactamente dónde hacer
  clic;
- priorizar la entrega de archivos completos, evitando ediciones manuales
  línea por línea cuando haya muchos cambios;
- explicar qué cambia, qué no cambia y cuál es el riesgo;
- no pedirle que diagnostique errores técnicos solo;
- responder en español, claro, directo y preciso.

Flujo habitual de implementación:

1. abrir el archivo en GitHub;
2. presionar el lápiz para editar;
3. Select All;
4. pegar el contenido nuevo;
5. escribir el mensaje de commit y confirmar;
6. refrescar la app con `Ctrl + F5`.

Para un archivo **nuevo**: *Add file → Create new file*, escribir la ruta
completa como nombre (ej. `historial/indices.json`), pegar, Commit.

Al proponer un cambio: explicar el objetivo, qué archivos toca, qué lógica
queda intacta, cuál es el riesgo; validar; entregar el archivo completo; dar
los pasos de GitHub en orden. Ser honesto sobre el alcance: si algo mejora
pero no queda perfecto, decirlo con números.

---

## 3. Trabajar siempre sobre la versión real

El usuario también modifica el proyecto desde otras herramientas, incluida
la sección de diseño de Claude. **Antes de tocar código, bajar SIEMPRE la
versión actual:**

```bash
curl -s https://raw.githubusercontent.com/nicofestu/Cartera/main/index.html -o /tmp/github_index.html
```

Si el cambio toca el benchmark o la reconstrucción histórica, bajar también:

```bash
curl -s https://raw.githubusercontent.com/nicofestu/Cartera/main/historial/indices.json
curl -s https://raw.githubusercontent.com/nicofestu/Cartera/main/historial/2026.json
```

Nunca asumir que una copia local está actualizada, que un archivo entregado
antes ya fue subido, ni que el estado recordado de una conversación anterior
coincide con `main`. Puede haber entregas anteriores sin subir.

---

## 4. Datos privados y seguridad

El repositorio es público. Los datos personales viven en un **gist secreto**
(ver `acceso_gist.md`), sincronizado desde la app con el botón Sync.

Son privados: movimientos, snapshots, saldos, precios manuales, cualquier
información derivada del portfolio, cualquier exportación del bróker, y la
fecha de inicio o el tamaño de la cartera del usuario.

**Regla absoluta: nunca escribir datos personales en el repo público ni en
ningún archivo de contexto.** No insertar en `index.html`, `historial/*.json`,
fixtures, comentarios ni en este documento: movimientos, snapshots, saldos,
tokens, el ID del gist como dato sensible, números de cuenta, PDFs o
extractos, ni nada que revele la cartera del usuario.

Los precios de mercado en `historial/` **no** son privados: son cotizaciones
públicas. Lo privado es qué tiene el usuario, y eso nunca sale del gist.

Nunca modificar el gist a mano desde el código público. Si hay que corregir
un dato histórico, se le entregan los valores al usuario para que los cargue
él desde la app.

---

## 5. Cómo se mide el benchmark

### Por qué no es un factor de calibración

Hasta 2026-07 el benchmark combinaba dos fuentes de distinta naturaleza:
cierres oficiales del índice (FRED) para el pasado, y el precio del CEDEAR
convertido a "puntos de índice" con un **factor de calibración fijo**
(`SPY_K`, `QQQ_K`) para hoy. El 2026-07-30 el S&P 500 cerró **+1,66%** y la
app mostró **−0,79%**: `indices.json` estaba atrasado cuatro ruedas (la
búsqueda de nivel no distinguía "cerrado" de "todavía no cargado") y el
factor de calibración estaba desactualizado, agregando un retorno inventado
que dependía de cuándo se había calibrado, no del mercado.

La medición de fondo (CEDEAR SPY en dólares vs. S&P 500, 4,53 años,
2022-01-18 → 2026-07-29: +59,33% vs. +59,84%, **−0,07% anual**) mostró que
no hay deriva sistemática entre el CEDEAR y el índice — lo que hay es
**ruido** (desvío diario 0,32% en condiciones normales, 1,18% en toda la
serie), y un factor fijo congela el ruido del día en que se calibró y lo
arrastra a toda ventana corta. Ese es el defecto de fondo, no la deriva.

### Arquitectura actual: tres fuentes encadenadas por retorno, nunca por nivel

**El benchmark se mide con la serie de retornos del CEDEAR. Nunca se
compara un nivel de una fuente contra un nivel de otra** — eso fue
precisamente el bug de arriba. La serie sintética se construye día a día
(`construirBench()`), probando en orden:

1. **El CEDEAR en dólares**, especie D (MEP) y, si ese día no operó, C
   (CCL) de respaldo — `usdEn()`. Fuente: `datos/precios/bench/{SPY,SPYD,
   SPYC,QQQ,QQQD,QQQC}.json`, archivo curado con precios reales del ETF,
   cobertura desde 2023-01-02. Las dos puntas de un cociente van SIEMPRE
   por la misma vía (D con D, o C con C): mezclar D con C adentro de una
   división lee el salto entre dos mercados como movimiento de precio
   (§6.7).
2. **`historial/{año}.json`** (el mismo archivo que escribe el Action de
   snapshot diario, `snapshot_historial.py`) para los días recientes que
   el archivo curado todavía no alcanzó — es la fuente rápida y siempre al
   día, a costa de ser menos curada que (1).
3. **El índice oficial** (FRED, `historial/indices.json`) **empalmado por
   RETORNO**, solo si las dos fechas del tramo existen literalmente en esa
   serie — acá no se usa relleno hacia atrás (`nivelEn()`): eso fue
   exactamente el bug original. Cubre lo que las dos fuentes de arriba no
   alcanzan (antes de 2023).

Si ninguna de las tres resuelve un tramo, no se inventa nada: se arrastra
la referencia anterior y se sigue sin perder el hilo (`out[f]` no se
escribe ese día).

**Filtro de cordura (`RATIO_OK`):** todo cociente entre dos ruedas tiene
que caer en (0,8, 1,25). Fuera de esa banda no es mercado — es un dato
roto o un cambio de ratio no declarado — y se descarta el tramo.

**Cambios de ratio del CEDEAR** (`AJUSTES_RATIO`, ver también §12): antes
de cualquier cociente, todos los precios se re-expresan a la escala vieja
multiplicando por el factor acumulado hasta esa fecha (`factorRatioPrecio`,
SIEMPRE activo acá — a diferencia del ajuste a nivel posición, que se
desactiva si el usuario ya cargó el split a mano, este es un hecho del
mercado y no depende de qué registró nadie). Sin esto, el día del split de
SPY (×3, 2026-05-29) se leería como una caída de precio de −66% y
`RATIO_OK` lo descartaría como dato roto.

**Dividendos** (`historial/dividendos.json`, claves `SPY`/`QQQ`): se
componen en la fecha ex (`factorDiv()`), en TODO tramo por igual —venga del
CEDEAR o del empalme oficial—, porque las dos fuentes son retorno de PRECIO
y las dos excluyen el dividendo. Formato: lista de `{ex, monto, px, frac}`
por ticker, ordenada por `ex`; el motor solo usa `frac` (=monto/px), la
fracción del precio que cae ese día — un monto absoluto no se le puede
sumar al CEDEAR, que está en otra escala.

**El nivel que se muestra es cosmético**: toda la serie arranca en 1 y al
final se multiplica por una constante que la ancla al primer cierre oficial
común. Una constante sobre toda la serie se cancela en cualquier cociente
— no por convención, por álgebra — y no interviene en ningún retorno.

**El de HOY** (`nivelHoyEncadenado()`) parte del último nivel conocido y lo
mueve con la variación EN VIVO del CEDEAR desde ese mismo día. Sin precio
en vivo, se devuelve el último nivel (retorno 0 hoy) — el dato honesto, no
uno inventado.

El gráfico y las cards leen la misma función. Nunca dos maneras de medir lo
mismo: ya ocurrió antes y llegaron a dar signos opuestos (§11).

### Consecuencias que hay que asumir

- **La card deja de medir el índice y pasa a medir el instrumento que
  realmente se puede comprar.** Es mejor benchmark —misma plaza, misma
  moneda, misma fricción— pero **no va a coincidir con el número del
  noticiero**. El rótulo tiene que decirlo, o el próximo que lo mire va a
  creer que está roto de nuevo.
- Con dividendos compuestos, el benchmark queda ~1% anual por encima del
  índice de precio para SPY y ~0,44% para QQQ. Es deliberado: la cartera
  propia también cobra dividendos y los suma al NAV, así que sin esto la
  comparación le regalaba esa diferencia a favor.
- El error de seguimiento diario del CEDEAR (mediana 0,18%, peor día ~1,35%
  en condiciones normales) pasa a ser parte del benchmark. Es real: es la
  volatilidad del instrumento que se podría haber comprado.

### Panel macro

Mostraba **niveles** de índices y commodities derivados de un factor
calibrado a mano (`MACRO_K`, en `indices.json`, ver más abajo). Al
2026-07-30 estaban desviados hasta 2% (oro). Decisión: **mostrar solo la
variación porcentual, sin nivel.** Un número de display equivocado sigue
siendo un número equivocado.

### `historial/indices.json` — formato y quién lo escribe

Contiene las series diarias de cierre de S&P 500 y Nasdaq 100 (fuente
FRED), que el motor de benchmark usa para el empalme oficial (fuente 3 de
arriba). Formato comprimido:

```json
{ "sp500": { "b": "2022-01-03", "g": [1,1,1,3,…], "v": [4796.56, 4793.54, …] },
  "ndx":   { … },
  "calibracion": { "SPY_K": 577.0, "QQQ_K": 787.7, "MACRO_K": { "sp": 577.0, … } } }
```

`b` = fecha del primer cierre, `v` = valores, `g` = huecos en días entre
cierres consecutivos (un número por hueco). Lo expande `expandirSerie()`.

**El campo `calibracion` es vestigial**: era la base del factor fijo que
motivó todo este rediseño (arriba) y ya no lo lee ningún camino de
cálculo — ni el benchmark principal (que usa retornos del CEDEAR + ratio,
no un factor) ni el panel macro (que ya no muestra niveles). Se conserva
en el archivo por compatibilidad hacia atrás, no por necesidad.

**El Action no lo toca**: `snapshot_historial.py` solo escribe
`historial/{año}.json`. **`indices.json` se edita a mano** y por eso se
atrasa — el diseño tiene que asumir que va a estar atrasado, no confiar en
que no lo esté (ver arriba, "por qué no es un factor de calibración").

Carga: `cargarBenchmarks()`, asíncrona y memoizada — junto con
`datos/precios/bench/*.json` y `historial/dividendos.json`, las tres
fuentes de la arquitectura de arriba. Arranca vacía; `nivelEn()` devuelve
`null` cuando no hay serie, así que hasta que termine la descarga la app
funciona igual y simplemente no dibuja la línea del índice.

**Trampa ya resuelta:** `cargar()` y `reconstruirHistorialSnapshots()`
guardan el nivel del índice dentro de cada snapshot, y esos snapshots van al
gist. Si el benchmark no cargó todavía, se fosilizaría un valor nulo en
datos permanentes. Ambas funciones esperan `await cargarBenchmarks()` antes
de escribir. **No quitar esos awaits.**

---

## 6. Reglas duras

Salen de errores ya cometidos. Cada una tuvo su costo.

1. **La caja siempre entra en el NAV.** El bug más caro de la historia del
   proyecto fue reconstruir cierres excluyendo el efectivo.
2. **Anualizar usa el calendario nominal, no la cantidad de datos.** Contar
   snapshots como días infla la TNA sin límite.
3. **Nada calibrado a mano en un camino que produzca un retorno.** §5.
4. **Un dato faltante se declara.** Si la serie no cubre la ventana pedida,
   no se dibuja la card. Es peor UI y es el dato honesto.
5. **Los parámetros y las series van en JSON del repo,** no en el código.
6. **Toda clave de nivel superior de `historial/AAAA.json` se trata como una
   fecha.** `cargarHistorialRemoto()` hace `Object.assign` de todos los años.
   Agregar cualquier otra clave contamina los bucles de backfill y de
   `detectarRatiosNoDeclarados()`.
7. **Las variaciones se encadenan entre precios obtenidos de la misma
   manera.** Mezclar el ticker en dólares con el ticker en pesos dividido el
   MEP dentro de un mismo cociente lee el salto entre métodos como
   movimiento de mercado.
8. **Los cambios de ratio de CEDEAR se declaran.** Un quiebre limpio de
   escala (×2, ×3, ×4, ×5, ×10 o inversos) no es mercado. Hay detección
   automática que avisa; hay que atenderla.
9. **Antes de tocar el código, bajar la versión real desde GitHub.** §3.
10. **Antes de entregar JS: `node --check` y chequeo de identificadores sin
    declarar.** Para lógica no trivial, además, smoke test en Node con `vm`
    y un control que demuestre que la versión anterior fallaba en el caso
    que se dice arreglar. Ver §15.
11. **No cambiar claves de `localStorage` sin migración explícita.** No
    cambiar la estructura de `DATOS` sin revisar compatibilidad. No
    invalidar movimientos ni snapshots existentes. No borrar propiedades
    desconocidas al restaurar o sincronizar. No tocar la lógica de Sync para
    cambios puramente visuales. No mezclar datos de prueba con datos reales.
    Antes de tocar persistencia o sincronización, revisar: `LS_KEY`,
    `DATOS`, `persistir()`, `persistirYSync()`, `restaurar()`,
    `subirNube()`, `bajarNube()`, importación y exportación.
12. **Los cambios visuales no deben modificar cálculos financieros.**
13. **Un ajuste de caja "declarado" (saldo real del bróker) no puede
    recalcularse dinámicamente contra la caja nativa en cada render.**
    Bug real, corregido el 2026-08-12: `saldoDeclaradoCta()` con
    `real:true` devolvía el valor declarado tal cual, y `ajusteNativoCta()`
    hacía `declarado − nativo(ahora)` en cada cálculo. Cualquier movimiento
    posterior (una venta, un depósito) subía la caja nativa y el ajuste
    bajaba en la misma magnitud, cancelándolo — la plata "desaparecía" del
    NAV y de la liquidez aunque el movimiento estuviera bien cargado. La
    corrección (`migrarSaldosRealesAjustes()`) convierte el saldo declarado
    en un ajuste FIJO, calculado una sola vez contra el cierre del día
    anterior, para que los movimientos posteriores se sumen en vez de
    cancelarse. Ese primer arreglo (hecho con ChatGPT, commit directo sin
    pasar por el pipeline de validación de §14-15) solo corría la migración
    al recargar la página o sincronizar — declarar un saldo y operar en la
    misma sesión sin recargar seguía perdiendo la plata. Claude lo confirmó
    con un smoke test (`vm`, sin datos reales) y agregó la llamada faltante
    en `guardarSaldos()`. **Lección para cartera-app (hito 7+, "saldos
    declarados por cuenta"):** diseñar el ajuste como un valor fijo desde
    el día uno (con fecha de vigencia explícita), nunca como una diferencia
    recalculada contra el estado corriente — evita esta clase de bug de
    raíz en vez de tener que migrarlo después.
14. **Un mismo concepto ("Rendimiento acumulado", "Retorno total") no puede
    tener dos fórmulas distintas en dos lugares de la pantalla.** Bug real,
    corregido el 2026-08-12 (madrugada): al migrar las cards de Histórico
    completo/YTD de money-weighted a time-weighted encadenado
    (`retornoEntre` sobre `serieDiaria()`), el gráfico de esa misma ventana
    quedó afuera del refactor y siguió usando la fórmula vieja
    (`serieRendimiento()`/`retHoy`). Resultado: la card decía +24% y el
    gráfico +15% para el mismo período, con la cartera ganándole a SPY en
    un lado y perdiéndole en el otro. El gráfico de los demás períodos
    (Hoy/Semana/Mes/1A) y el mini-gráfico de Inicio (`serieMiniInicio()`)
    ya usaban el motor correcto — sirvieron de referencia para el arreglo.
    Mismo principio que ya regía el benchmark (§5: "el gráfico y las cards
    leen la misma función, nunca dos maneras de medir lo mismo"), aplicado
    acá también. Al tocar cualquier cálculo de rendimiento, verificar que
    TODOS los lugares que lo muestran (cards, tabla comparativa, gráfico
    grande, mini-gráfico de Inicio) sigan leyendo la misma fuente.

---

## 7. Arquitectura: por qué NO separar `index.html`

Pregunta ya evaluada y resuelta. **No separar el código en varios archivos.**

Motivo operativo, no estético: la app se sirve desde GitHub Pages y el
usuario la actualiza pegando el archivo en el editor web. Partirla en
`index.html` + `app.js` + `style.css` convierte cada cambio en varios commits
coordinados, y un archivo desfasado rompe la app entera sin dar un error
claro. La simplicidad operativa es prioridad.

Los números tampoco lo justifican: dentro del JS, análisis con `espree` +
`eslint-scope` no encuentra funciones duplicadas ni desorden estructural. El
archivo se siente grande por tablas de datos pegadas, no por desorden.

**La palanca real es sacar DATOS, no código.** Ya hecho: series de índices
(§5). Pendiente y ofrecido, sin respuesta: `COMAFI` (~27 KB, tabla de
nombres/sectores de CEDEARs, usada en importadores y en la pestaña Mercado)
→ `datos/cedears.json`. Candidatos menores: `NOMBRE_AR`, `EMISOR_ON`.

---

## 8. Vistas ARS / MEP / CCL y base de comparación

`VISTA` puede ser `"ARS"`, `"MEP"` o `"CCL"` y controla la moneda de
valuación de Inicio, Rendimientos, Movimientos y Mercado.

La regla:

> Los **montos** (NAV, liquidez, valuación, asignación) se muestran en la
> moneda elegida. Todo lo que se **divide** por un costo o por un aporte
> (retornos, P&L, contribución) se mide siempre en base ARS / USD MEP.

Motivo: el costo promedio y el capital aportado se llevan en dólares MEP —es
el tipo de cambio al que entró cada peso— y **no existe una serie CCL
histórica por movimiento**. Valuar hoy a CCL y dividir por una base MEP mete
la brecha entre los dos dólares adentro del rendimiento como si fuera
resultado de la cartera.

Consecuencia buscada: los porcentajes de MEP y CCL son idénticos; los montos
absolutos no.

Si en algún momento se quiere un CCL histórico real, hace falta una serie
diaria de CCL y un campo `ccl` por movimiento, análogo a `mep`. Es un cambio
grande: evaluar contra §18 (fuentes) antes de encararlo.

---

## 9. Serie de rendimiento, Modified Dietz y pausa por capital bajo

`serieRendimiento()` distingue **aportes de capital externo** de la
**rotación interna** de cartera. Una venta acredita caja; una compra consume
caja y solo el faltante cuenta como aporte nuevo. Depósito = aporte.
Dividendos y gastos mueven la caja pero **no** son capital que entró o salió:
son resultado.

`serieDiaria()` usa **Modified Dietz**: cada flujo pesa por la fracción del
tramo que estuvo efectivamente invertido. El criterio viejo
(`r = (v1 − flujo)/v0 − 1`) asumía que todo el capital entraba justo al
cierre del tramo y producía saltos verticales absurdos con depósitos grandes
sobre carteras chicas. No revertir.

`ORDEN_CAJA` fija el orden dentro de un mismo día: lo que acredita plata
(venta, depósito, dividendo) liquida antes que lo que la gasta. Sin esto, una
compra financiada por una venta del mismo día se contabiliza como capital
nuevo e infla el denominador del retorno.

`capitalVigenteUSD(hitos, f)`: cuando aportado − retirado ≤ ~USD 100, la
cartera y el benchmark simulado dejan de acumular rendimiento. Evita que el
índice "corra" en períodos sin plata invertida. **No eliminar esta pausa.**
`serieDiaria()` además descarta días con menos de US$100 de NAV.

---

## 10. Métricas de riesgo

`metricasRiesgo()` fue reescrita el 28/07/2026. Punto clave:

> **Los tramos de `serieDiaria()` no son todos de un día.** Cuando faltan
> cierres —fin de semana largo, días sin abrir la app, huecos de cobertura de
> precios— un solo punto puede cubrir 10, 20 o 40 días de calendario.

La versión anterior trataba cada punto como una rueda y anualizaba con
`252/n`, es decir sobre la **cantidad de cierres cargados** en vez del
tiempo transcurrido. Resultados medidos sobre dos años simulados
(volatilidad real 17,5%, retorno 14,6%, Sharpe 0,83):

| Cadencia real de cierres | Corregido | Versión vieja |
|---|---|---|
| cada 3 días | vol 21,2% · ret 14,6% · Sharpe 0,69 | vol 30,6% · ret 32,6% · Sharpe 1,07 |
| cada 7 días | vol 21,4% · ret 14,6% · Sharpe 0,68 | vol 47,0% · ret 93,3% · Sharpe 1,98 |
| cada 14 días | vol 24,8% · ret 14,6% · Sharpe 0,59 | vol 77,1% · ret 273,5% · Sharpe 3,55 |
| cada 30 días | vol 17,9% · ret 14,1% · Sharpe 0,79 | vol 82,3% · ret **1450%** · Sharpe **17,63** |

Cómo se corrigió: cada observación se estandariza a "una rueda"
(`u = ln(1+r) / √ruedas`); los días de calendario se convierten a ruedas con
`× 252/365`; el retorno anualizado usa los días de calendario efectivamente
cubiertos; beta y correlación usan la misma estandarización; la máxima caída
no se tocó, es un encadenamiento y no dependía de esto. Con serie 100% diaria
el resultado es idéntico al de antes.

Alcance honesto: el retorno anualizado queda prácticamente exacto en toda la
grilla; la volatilidad deja de estar sistemáticamente inflada pero sigue
siendo una estimación ruidosa —con 26 o 52 observaciones no se puede
recuperar con precisión la volatilidad diaria, eso es irreducible—. La UI lo
dice: rotula "tramos", no "retornos diarios".

---

## 11. Reconstrucción de snapshots históricos

`reconstruirHistorialSnapshots()` completa `DATOS.snapshots` hacia atrás
usando `historial/*.json`.

Reglas vigentes:

- un snapshot capturado **en vivo** (sin `hist:true`) nunca se toca: tiene
  precios reales al momento, más confiables que un cierre de fin de día;
- un snapshot `hist:true` se recalcula si la reconstrucción es completa y
  difiere más que el margen (`TOL_ABS = 500`, `TOL_REL = 0,002`);
- si la reconstrucción es parcial, solo se repara el caso cuya firma es
  exactamente el bug conocido (lo guardado coincide con las posiciones
  **sin** la caja);
- no se fabrica un cierre nuevo si falta algún precio;
- la caja se suma siempre, nunca depende de la cobertura de precios.

**Tipos que bloquean:** solo `manual` y `on` bloquean por falta de cobertura
automática. `accion`, `cedear` y `fci` tienen datos. No ampliar esa lista sin
revisar la cobertura real de `historial/*.json`.

### El bug del FCI (corregido 28/07/2026) — leer antes de tocar esto

La búsqueda de precio de un FCI usaba `p.ticker`, pero los movimientos de FCI
no siempre tenían un ticker usable. **La búsqueda fallaba siempre**, el día
entero quedaba marcado "sin cobertura" y no se generaba ningún cierre. Un
parche manual en `historial/2026.json` era inalcanzable desde el código:
estaba el dato, pero nadie lo podía encontrar.

Se agregó `clavesHistFci(p)`, que resuelve la clave probando, en orden: (1)
`p.ticker` si existe y no es el literal `"FCI"`; (2) la clave de
`historial/*.json` que sea prefijo del nombre normalizado del fondo —
normalizando a mayúsculas sin acentos ni separadores. Gana la clave más
larga que encaje, para que un nombre corto no tape a uno largo. Se cachea en
`FCI_CLAVE_HIST`. Si un fondo no tiene cobertura, devuelve lista vacía y no
inventa nada.

**Corolario general:** un dato puede estar presente y ser inalcanzable. Antes
de concluir "falta cobertura", verificar que la búsqueda esté usando la
clave correcta.

### Campo `ticker` en movimientos de FCI

Un movimiento de FCI guarda el nombre largo del fondo en `fondo` y además un
`ticker` corto. **El ticker no es decorativo: es la clave con la que el
fondo figura en `historial/*.json`.** Se perdía por dos caminos, ya
corregidos: el importador no lo copiaba, o el alta manual guardaba el
literal `"FCI"`. Si se toca el importador o el formulario de alta,
**conservar el ticker del FCI**.

---

## 12. Cambios de ratio de CEDEARs

Cuando cambia el ratio de un CEDEAR, el precio cambia de **escala** de un día
para el otro y el tenedor recibe papeles nuevos. En `movimientos` no se
carga nada, así que las cantidades siguen en la escala vieja y sin corregir
la cartera parece desplomarse.

Piezas: `AJUSTES_RATIO`, `factorRatio()`, `ratioCargadoAMano()`,
`detectarRatiosNoDeclarados()`. `factor` = cuántos papeles nuevos entrega
cada papel viejo. Caso declarado: SPY, 29/05/2026, factor 3.

Si el usuario ya cargó el ajuste como un movimiento (una compra a precio 0),
`ratioCargadoAMano()` desactiva el ajuste automático para ese ticker: si no,
la corrección se duplicaría.

Antes de tocar un ratio: verificar que el quiebre de escala sea limpio, la
fecha, el factor, y que no esté ya cargado a mano.

---

## 13. Fondo NASA

Consume `https://images-api.nasa.gov`. Temas: Tierra y Luna vistas desde el
espacio. Filtra personas, renders, diagramas, logos e imágenes chicas —por
**metadatos** (título, descripción, keywords, fotógrafo), no por píxeles, así
que es best effort.

No revertir: resolver varias URLs del manifest, priorizar `orig`, luego
`large`, `medium`, `small`; probar varios archivos; aceptar desde ~1600×900;
cachear por sesión; nunca bloquear la app si NASA falla.

---

## 14. Validación obligatoria de JavaScript

Después de cualquier cambio en JS:

1. extraer el bloque `<script>` más largo del HTML, guardarlo como `.js`;
2. correr `node --check archivo.js`. **No entregar cambios si falla.**
3. verificar etiquetas balanceadas (`<script>`, `<style>`) y llaves,
   paréntesis, template strings.

### Chequeo de identificadores sin declarar

Barato, atrapa typos que `node --check` no ve:

```bash
npm install espree eslint-scope --silent
```

```js
const espree=require('espree'), escope=require('eslint-scope');
const ast=espree.parse(src,{ecmaVersion:2022,loc:true,range:true}); // range:true obligatorio
const sm=escope.analyze(ast,{ecmaVersion:2022});
const globalesOk=new Set(['document','window','fetch','localStorage','sessionStorage',
  'alert','confirm','navigator','XLSX','pdfjsLib','console','Math','Date','JSON', /* …builtins… */]);
const sospechosos=[...new Set(sm.globalScope.through.map(r=>r.identifier.name))]
  .filter(n=>!globalesOk.has(n));
```

Sin `range:true`, `eslint-scope` tira
`TypeError: Cannot read properties of undefined (reading '0')`.

---

## 15. Smoke tests con Node y `vm`

Para parsers, importadores, cálculos financieros, reconstrucción de
snapshots, normalización de precios y conversiones de moneda: cargar el
script en un contexto `vm` con stubs mínimos y llamar directo a la función.

```js
const vm=require('vm');
const el=()=>({textContent:"",innerHTML:"",value:"",style:{},
  classList:{add(){},remove(){},toggle(){}},querySelector:()=>null,
  querySelectorAll:()=>[],addEventListener(){},setAttribute(){},
  getBoundingClientRect:()=>({width:0}),insertAdjacentHTML(){},dataset:{}});
const ctx={console,Math,Date,JSON,Object,Array,String,Number,Boolean,Promise,
  Set,Map,WeakMap,RegExp,Error,isNaN,isFinite,parseFloat,parseInt,encodeURIComponent,
  // TRAMPA 1: si setInterval es el real, el proceso nunca termina (el init de
  // la app arranca dos intervalos). Stubearlo o el test se cuelga hasta el timeout.
  setTimeout:(f,t)=>{ if(!t) f(); return 0; }, clearTimeout:()=>{}, setInterval:()=>0,
  document:{getElementById:()=>el(),querySelector:()=>null,querySelectorAll:()=>[],
    addEventListener(){},createElement:()=>el(),body:el(),
    documentElement:{style:{setProperty(){}}}},
  window:{},localStorage:store,sessionStorage:store,alert:()=>{},confirm:()=>true,
  navigator:{},fetch:()=>Promise.reject(new Error('sin red')),
  Blob:function(){},URL:{createObjectURL:()=>"",revokeObjectURL(){}},
  FileReader:function(){},Image:function(){},XLSX:{},pdfjsLib:{GlobalWorkerOptions:{}}};
ctx.globalThis=ctx; ctx.self=ctx;
vm.createContext(ctx);
vm.runInContext(src,ctx);
```

**TRAMPA 2, la más importante:** `DATOS`, `VISTA`, `ESTADO`, `SP500_HIST` y
casi todo el estado están declarados con `let`/`const`, y **las
declaraciones léxicas no quedan como propiedades del objeto de contexto**.
`ctx.DATOS` es `undefined`. El código del test tiene que correr *dentro* del
contexto con `vm.runInContext`. Solo las `function` declaradas de nivel
superior son accesibles como `ctx.nombre`.

Para probar carga de datos remotos sin red, stubear `fetch` para que sirva
el JSON local y rechace todo lo demás.

**Calidad de los fixtures:** datos realistas y anonimizados, nunca sparse.
Cubrir múltiples cuentas, compras y ventas el mismo día, depósitos, retiros,
ARS y USD, posiciones faltantes, períodos sin capital invertido, precios
faltantes y cambios de ratio.

**Incluir siempre un control:** verificar que la versión vieja del cálculo
efectivamente fallaba en el caso que se dice estar arreglando. Sin eso, un
test puede pasar y no demostrar nada.

**Playwright no está disponible en el sandbox** (falta `libXdamage.so.1`,
sin `sudo`). No perder tiempo intentándolo, no prometer validación visual
automatizada, no tratar un fallo de Playwright como un fallo de la app.

**Diferenciar siempre y con claridad, al reportar:** validación sintáctica,
smoke test de lógica, inspección manual, prueba real en navegador. No decir
que algo fue probado si solo se revisó el código.

---

## 16. Entrega de cambios

Archivo completo cuando haya muchos cambios, con el nombre correcto,
indicando qué reemplaza, qué lógica queda intacta y cuál es el riesgo.
`present_files` para el enlace y recordar el procedimiento de GitHub. No
pedirle al usuario que copie fragmentos sueltos.

Bloque acotado cuando el cambio sea chico y localizado: texto exacto a
buscar, comienzo y final, reemplazo, mensaje de commit.

**Cuando hay más de un archivo, indicar el ORDEN de subida.** Importa:
ejemplo real, `historial/indices.json` va antes que `index.html` — al revés,
entre un commit y el otro la app se queda sin la línea del índice (no se
rompe, pero desaparece).

Antes de entregar: comparar contra la versión real de GitHub (§3), conservar
las correcciones existentes, validar sintaxis (§14) y verificar las
funciones críticas con smoke test (§15).

**Este flujo (archivo completo / bloque acotado + pegar en el editor web)
es el de Cartera.** En cartera-app, cuando el usuario autoriza el commit
directo (compartiendo un token), la entrega es el commit mismo vía API —
ver §23 para la disciplina de SHA, verificación previa y orden de subida
en ese contexto.

---

## 17. Diseño e identidad visual

Inspiración: SpaceX, Tesla, interfaces aeroespaciales, telemetría, dashboards
financieros profesionales.

Mantener: fondo negro profundo, alto contraste, tipografía sans técnica para
títulos y monoespaciada para cifras, acentos fríos, verde y rojo reservados
para datos positivos y negativos, animaciones discretas, densidad
informativa, jerarquía clara.

Evitar: estilo Bootstrap, Material Design genérico, estética de banca
tradicional, colores decorativos, tarjetas muy redondeadas, sombras
exageradas, íconos sin función, cualquier cosa que sacrifique legibilidad en
tablas.

Prioridad visual: NAV → rendimiento del día → P&L → liquidez → asignación →
posiciones → gráfico → datos secundarios.

**Los cambios visuales no deben modificar cálculos financieros** (regla 12
de §6).

---

## 18. Cobertura histórica y fuentes

Antes de modificar el sistema de precios, distinguir: datos reales de BYMA,
datos públicos de terceros, series embebidas, precios manuales,
estimaciones, interpolaciones e historial generado por el Action. No mezclar
categorías sin dejar claro el origen, y no convertir una estimación puntual
en una supuesta fuente automática.

Al evaluar una fuente nueva, revisar: CORS, disponibilidad, términos,
formato, estabilidad, resolución temporal, moneda, unidades, splits y
ratios.

### Cobertura verificada al 2026-07-30

| serie | desde | ruedas | notas |
|---|---|---|---|
| CEDEAR SPY (ARS) | 2022-01-18 | 1.088 | cambio de ratio ×3 el 2026-05-29, declarado |
| CEDEAR QQQ (ARS) | 2025-01-02 | 382 | **no cubre 2022–2024** |
| SPYD / QQQD (USD) | 2026-07-27 | 3 | el scraper los agregó recién |
| S&P 500 y Nasdaq 100 (FRED) | 2022-01-03 | 1.146 | `indices.json`, se edita a mano |
| MEP histórico | — | — | fuente externa; respaldo en los snapshots propios |

El hueco de QQQ 2022–2024 es exactamente el caso que justifica conservar las
series oficiales del índice: una cartera que arranque en 2023 necesita ese
empalme (§5, "Decisión"). Es también la razón por la que `indices.json` **no
se borra**.

### Limitaciones conocidas

- **`manual` y `on`**: sin cobertura automática. Cuando alguno esté en
  cartera, bloquea la reconstrucción de esos días. Si aparece un gráfico
  plano, interpolado, con huecos o con saltos: revisar primero la cobertura
  de precios, no asumir que los movimientos o el gist están mal.
- **Parches manuales de acciones/CEDEARs poco comunes**: sourceados a mano,
  no forman parte del scraper automático. Si el Action no se actualiza, el
  problema puede repetirse con instrumentos nuevos.
- **FCI interpolados**: cuando la fuente no tiene cotización diaria, se
  interpola geométricamente entre dos puntos reales. Razonable para un money
  market de baja volatilidad, pero no es cotización oficial diaria y no debe
  presentarse como tal.
- **CCL histórico**: no existe. Ver §8.
- **Volatilidad con pocos cierres**: ver §10, sigue siendo ruidosa aunque ya
  no esté sesgada.

---

## 19. Forma de razonar sobre errores

Cuando aparezca un salto o un dato extraño, revisar **en este orden**:

1. cobertura de precios;
2. moneda y tipo de cambio;
3. cambio de ratio o split;
4. posición sin precio;
5. movimiento faltante;
6. orden de movimientos del mismo día;
7. caja;
8. snapshot incompleto;
9. sincronización;
10. error de cálculo.

No asumir de entrada que el gist está mal. No corregir números a mano sin
identificar la causa raíz.

---

## 20. Checklist de regresión después de cada cambio

**Inicio:** NAV, rendimiento del día, P&L, liquidez, asignación por clase y
por cuenta, posiciones, fondo NASA.

**Rendimientos:** gráfico, benchmark S&P 500 y Nasdaq 100, selector de
período, tooltip, crosshair, pausas por capital bajo, métricas de riesgo,
diagnóstico de la serie.

**Monedas:** cambiar entre ARS, MEP y CCL. Los porcentajes de MEP y CCL
tienen que ser idénticos; los montos absolutos no.

**Movimientos:** alta, edición, borrado, filtros, total, cantidades, moneda,
MEP del movimiento, múltiples cuentas.

**Mercado:** panel macro, buscador, filtros, subtabs, datos, timestamps.

**Modales:** movimiento, precio manual, saldos, Sync, importación.

**Persistencia:** recargar, confirmar que los datos persisten, que Sync
sigue funcionando y que no se alteraron datos existentes.

**Historial:** que el gráfico no introduzca saltos nuevos, revisar cobertura
y snapshots reconstruidos, no modificar el gist a mano.

**Benchmark:** con `historial/indices.json` presente y también **sin** él
(simular fallo de red): la app tiene que seguir funcionando, solo sin la
línea del índice.

---

## 21. Regla maestra

La meta no es producir código. Es evolucionar una aplicación financiera
personal **pensada para escalar** (§1) sin perder datos, sin publicar
información privada, sin revertir correcciones anteriores, sin introducir
saltos falsos, sin confundir problemas de precios con problemas de
movimientos y sin exigirle conocimientos técnicos al usuario.

---

## 22. Pendiente

- Implementar §5: motor de benchmark sobre retornos del CEDEAR con empalme y
  dividendos.
- Crear `historial/dividendos.json` y definir quién lo mantiene.
- Revisar si el nivel de índice guardado dentro de cada snapshot (`sp`,
  `ndx`) sigue teniendo sentido: hoy se escribe al gist y no lo lee nadie
  para calcular retornos.
- Cobertura de QQQ anterior a 2025 en `historial/AAAA.json`, si aparece
  fuente.
- Sacar `COMAFI` a `datos/cedears.json` (−27 KB) — ofrecido, sin respuesta.
- Actualizar el scraper para cubrir más categorías (`on`, `manual`, más FCI).
- Evaluar una fuente sostenible para FCI.
- Mejorar consistencia visual entre pestañas y la experiencia en móvil.
- Mejorar diagnósticos.

Evaluar cada mejora contra estabilidad, mantenimiento y el principio rector
de §1.

---

## 23. cartera-app — disciplina de cambios seguros

Repo: `nicofestu/cartera-app` (privado). Stack: Next.js + TypeScript, App
Router, Supabase (`@supabase/ssr`) para auth y base de datos, desplegado en
Vercel con deploy automático desde `main`.

```
app/auth/callback/route.ts   intercambia el link de confirmación por sesión
app/login/, app/signup/      formularios (Server Actions)
app/dashboard/                área autenticada
app/actions.ts                Server Actions: signIn, signUp, signOut
lib/supabase/client.ts        cliente para componentes de navegador
lib/supabase/server.ts        cliente para Server Components / Actions
middleware.ts                 protege /dashboard, redirige sesiones activas
supabase/schema.sql           esquema de base de datos
```

Con múltiples usuarios reales, un cambio mal hecho ya no arruina un solo
archivo local: puede exponer datos de una persona a otra, romper el login
de todos, o silenciosamente empezar a mezclar información entre cuentas.
Por eso, para este repo, se suma a todo lo anterior (§3, §14, §15, §16):

**1. Nunca asumir el estado del repo — verificar siempre antes de escribir.**
Antes de tocar cualquier archivo, traer su contenido y su `sha` actual vía
la API de contenidos de GitHub (`GET /repos/.../contents/{path}`), igual
que se hizo para `route.ts` y `page.tsx`. El commit vía API (`PUT
/contents/{path}`) requiere ese `sha`: si alguien más (el usuario, Vercel,
otra sesión) tocó el archivo mientras tanto, el `sha` no matchea y GitHub
**rechaza el commit** en vez de pisarlo. No forzar ese chequeo ni
reintentar con un `sha` viejo — volver a bajar el archivo y reevaluar.

**2. Cada archivo que se modifica se valida antes de subir, no después.**
Mínimo: chequeo sintáctico (parser de TypeScript/JSX — ver ejemplo real
usado para `route.ts`/`page.tsx`). Cuando el cambio toca lógica de datos
(queries a Supabase, RLS, Server Actions que escriben), preferir inspección
manual explícita de qué usuario puede leer/escribir qué fila, en vez de
asumir que el cliente ya filtra correctamente.

**3. Row Level Security (RLS) es la frontera entre usuarios — nunca se
desactiva ni se bypassea "para probar".** Toda tabla en `supabase/schema.sql`
que contenga datos de usuario necesita policies de RLS activas. Un cambio de
esquema que agregue una tabla sin policy es, por defecto, un cambio que dejó
los datos de todos los usuarios visibles para todos los usuarios. Antes de
dar por cerrado un cambio de esquema: confirmar explícitamente qué policy
aplica y qué usuario queda excluido.

**4. Las migraciones de base de datos se registran, nunca se aplican solo
a mano desde el dashboard de Supabase.** Si un cambio de esquema se hizo
manualmente por urgencia, el paso siguiente es escribirlo en
`supabase/schema.sql` (o en un archivo de migración versionado) para que
el repo refleje el estado real de la base. Un esquema que solo existe en el
dashboard de Supabase y no en el repo es un cambio que se puede perder o
duplicar sin que nadie lo note.

**5. Nada se pisa: preferir Server Actions y RLS por sobre lógica en el
cliente,** para que un usuario no pueda, manipulando el navegador, escribir
o sobreescribir datos de otro. La validación de "esto es tuyo" ocurre en el
servidor (Server Action + policy de Supabase), no solo en la UI.

**6. Los cambios no se commitean directo a `main` — pasan por una rama y un
Preview Deployment antes de mergear.** Flujo estándar para cualquier cambio
en cartera-app, salvo que el usuario pida explícitamente saltarlo:

1. Crear una rama nueva desde `main` (vía API: `POST /git/refs`), con
   nombre descriptivo (`fix/auth-callback-token-hash`,
   `feat/importador-cocos`, etc.).
2. Commitear los cambios a esa rama, no a `main` (mismo mecanismo de §23.1,
   pasando `branch` en el body del `PUT /contents/{path}`).
3. Abrir un Pull Request de esa rama contra `main` (`POST /pulls`).
4. Avisarle al usuario el link del PR. Vercel genera automáticamente un
   Preview Deployment por PR — el link aparece en los checks del PR o en el
   dashboard de Vercel. Pedirle al usuario que lo pruebe ahí, no en `main`.
5. **Mergear el PR solo después de que el usuario confirme explícitamente**
   que probó el preview y está conforme. No asumir que "el build pasó" en
   Vercel equivale a que el usuario ya lo vio funcionar.
6. Si el usuario pide explícitamente saltar este flujo (cambio trivial,
   apuro puntual), commitear directo a `main` como antes, pero dejarlo
   explícito en la respuesta: "esto se sube directo a `main`, sin preview".

Antes de un cambio con riesgo de romper el login o el acceso a datos
(middleware, callback de auth, policies, variables de entorno), además:
explicitar qué pasa con una sesión ya iniciada, qué pasa con un usuario a
mitad del flujo de signup, y cómo se revierte si algo sale mal (ver §24
para secretos).

**7. Distinguir siempre, igual que en §15 para Cartera:** chequeo
sintáctico ≠ compilación real de Next.js con los tipos del proyecto ≠
prueba en navegador. No hay Playwright ni el toolchain completo de
Next.js/Supabase en este entorno — decirlo explícitamente cuando aplique,
no dar a entender que se corrió el build real si no se corrió.

---

## 24. Secretos y tokens

cartera-app maneja credenciales reales: claves de Supabase, y cuando el
usuario decide compartir uno, un Personal Access Token de GitHub con
permisos de escritura sobre el repo privado.

- **Un token que el usuario pega en el chat se usa para esa conversación y
  no se guarda en memoria persistente entre sesiones — ni siquiera si el
  usuario lo pide explícitamente.** Si hace falta en una conversación
  nueva, se vuelve a pedir. No se escribe en `PRINCIPIOS.md`, en las
  instrucciones del proyecto, ni en ningún archivo de project knowledge:
  es una credencial de escritura sobre un repo privado, no un dato de
  contexto. Esto ya es la práctica seguida y se deja documentado acá para
  que no cambie.
- Recomendar siempre: tokens *fine-grained*, acotados al repo puntual,
  con expiración corta, y permiso de "Contents" al mínimo necesario (solo
  lectura si no hace falta escribir).
- Nunca proponer pegar un secreto (API key, contraseña, token) en un archivo
  del repo, en un componente de cliente (`"use client"`), ni en cualquier
  variable `NEXT_PUBLIC_*` — esas quedan expuestas en el bundle del
  navegador. Los secretos van solo en variables de entorno server-side de
  Vercel, leídas desde Server Actions / Route Handlers / Server Components.
- Después de un uso puntual del token, recordarle al usuario la opción de
  revocarlo desde `Settings → Developer settings → Personal access tokens`,
  igual que se hizo acá.
- **`SUPABASE_SERVICE_ROLE_KEY` es un secreto de máximo riesgo: se salta
  Row Level Security por completo, para cualquier tabla, de cualquier
  usuario.** Mismas reglas que un token de GitHub y una más: además de
  vivir solo en variables de entorno server-side de Vercel (nunca
  `NEXT_PUBLIC_*`, nunca en un componente cliente), el código que la usa
  (`lib/supabase/admin.ts`) tiene que quedar acotado a jobs de sistema sin
  usuario (hoy, solo `app/api/cron/snapshot`) — nunca usarla para responder
  una request de un usuario común, ni siquiera "para simplificar" una
  consulta puntual. Si aparece una segunda razón para necesitarla, se
  evalúa igual de estricto, no se da por sentado que ya está aprobada
  porque ya se usa en otro lado.

---

## 25. Checklist de regresión — cartera-app

Antes de dar un cambio por terminado en este repo, repasar:

**Auth:** signup con email nuevo, confirmación de email (banner visible),
login, logout, intento de entrar a `/dashboard` sin sesión (debe redirigir
a `/login`), intento de ver `/login` o `/signup` con sesión activa (debe
redirigir a `/dashboard`).

**Aislamiento entre usuarios:** con dos cuentas de prueba, confirmar que
ninguna puede leer ni escribir datos de la otra — ni por la UI ni
consultando la tabla directamente si hay acceso al dashboard de Supabase.

**Despliegue:** el cambio pasó por una rama + PR con Preview Deployment
(§23.6), no se commiteó directo a `main` salvo excepción explícita; el
usuario confirmó haber probado el preview antes del merge; las variables de
entorno necesarias existen en Vercel para el ambiente correspondiente
(Preview y Production pueden tener valores distintos — confirmarlo si el
cambio toca configuración).

**Nada roto en lo que ya andaba:** login/logout de una cuenta que ya
funcionaba antes del cambio, siguen funcionando después.

Este checklist crece a medida que cartera-app sume funcionalidad
(portfolios, movimientos, importadores) trayendo lógica desde Cartera —
cada pieza portada debería sumar acá su propia línea de regresión.

---

## 26. Objetivo final de cartera-app y plan de hitos

**Meta explícita:** cartera-app tiene que llegar a ser, en funcionalidad,
un calco de Cartera (nicofestu/Cartera) — multiusuario, con la misma
lógica financiera ya validada en el legado — no una versión reducida
permanente. Que hoy cubra menos no es el diseño final: es el estado
intermedio de un plan en curso. Esta sección es ese plan, y se actualiza
a medida que se completa cada hito o se decide dejar algo afuera a
propósito (lo segundo se anota acá también, explícitamente, para que no
se confunda con "todavía no llegamos").

### Núcleo financiero (hitos 1-6)

1. **Valuación de mercado y NAV** — ✅ hecho (2026-08-11, PR #1, merge
   `865febe3`). Precios en vivo (data912.com), VCP de FCI
   (argentinadatos.com), MEP/CCL (dolarapi.com), NAV total, liquidez por
   pool, P&L no realizado por posición, en `/dashboard/cartera`.
   Simplificaciones declaradas y pendientes de cerrar más adelante: sin
   factor de ratio de CEDEAR, caja sin liquidación T+n ni saldos
   declarados (ver hito 7 más abajo).
2. **Cauciones** — ✅ hecho (2026-08-11, PR #1 [sic, ver commits directos a
   `main`]). Alta colocadora/tomadora, las 3 patas sintéticas ligadas por
   `grupo_caucion`, interés devengado sumado al NAV. Simplificación
   declarada: el MEP de cada pata usa el MEP en vivo al momento de la
   carga, no una serie histórica por fecha (mepDeFecha no está portado
   todavía — ver hito 5).
3. **Snapshot diario de NAV — mejora deliberada sobre Cartera legado**
   (2026-08-11, PR #2). En Cartera legado el snapshot personal (a
   diferencia del historial de PRECIOS de mercado, que sí corre solo vía
   GitHub Action) solo se grababa si el usuario abría el navegador — un
   día sin visitas era un día sin dato. cartera-app SÍ tiene backend, así
   que se aprovechó para hacerlo mejor, no solo igual: un Vercel Cron Job
   (`vercel.json`, `app/api/cron/snapshot`) corre lunes a viernes 21:30 UTC
   (mismo horario que la Action de historial de Cartera) y graba el NAV de
   TODOS los usuarios sin depender de que nadie entre a la app. Usa un
   cliente Supabase con la service role key (`lib/supabase/admin.ts`, ver
   §24 para el manejo de ese secreto) porque necesita leer datos de
   usuarios sin sesión activa — es el único lugar del código que debería
   usar ese cliente. El cálculo de NAV se compartió entre la página y el
   cron (`lib/cartera/nav.ts`, función `calcularNav`) para que no haya dos
   lugares calculando el mismo número de formas distintas.
   Este es un ejemplo del criterio general: cuando cartera-app tiene una
   capacidad real que Cartera legado no podía tener (backend, cron), no
   hay obligación de copiar la limitación del legado — se declara la
   mejora acá, explícitamente, para que quede claro que es una decisión y
   no una copia parcial.
4. **Migración de datos históricos del gist legado** — pendiente, subida
   de prioridad el 2026-08-11 a pedido explícito del usuario: "que toda la
   data histórica que en su momento bajamos y todos los snapshots de la
   app vieja no sea info perdida — que se aproveche en la nueva app". Dos
   partes:
   - **`DATOS.movimientos` del gist** → tabla `movimientos` de
     cartera-app. Mapeo directo campo a campo (mismo significado); es lo
     más valioso de migrar, porque hoy cartera-app no tiene ningún
     movimiento real cargado, solo pruebas.
   - **`DATOS.snapshots` del gist** → tabla `snapshots` de cartera-app.
     Con un matiz: el legado calculaba esos NAV históricos con más años de
     ajustes de los que cartera-app ya porteó (factor de ratio de CEDEAR,
     liquidación T+n, etc. — ver hito 7 más abajo), así que un snapshot
     viejo no es 100% comparable con uno calculado hoy por `calcularNav`.
     Igual se migran tal cual (con esa salvedad declarada, no silenciada):
     da la curva de rendimiento completa desde el día 1 en vez de arrancar
     de cero con el cron nuevo.
   Se prioriza ANTES de cerrar Rendimientos (hito 5) porque cuanta más
   historia real haya cargada, más preciso sale todo lo que ese hito
   calcula (retorno acumulado, TIR, benchmark).
5. **Rendimientos** — en curso. Retorno acumulado sobre los snapshots
   (`lib/cartera/rendimiento.ts`) ✅ hecho (2026-08-11). Retorno por tramo
   con Modified Dietz (`serieDiaria()`) ✅ hecho (2026-08-12). TIR (XIRR)
   y selector de período (Hoy/Semana/Mes/YTD/1A/Todo) ✅ hecho (2026-08-12).
   Benchmark contra S&P 500 y Nasdaq 100 (`lib/cartera/benchmark.ts`, nuevo)
   ✅ hecho (2026-08-12) — motor de retornos del CEDEAR con empalme oficial
   (FRED) y `historial/{año}.json` como HIST_REMOTO para el tramo reciente,
   dividendos compuestos en la fecha ex, y ajuste de ratio (SPY ×3). Tabla
   comparativa "Tu cartera / SPY / QQQ" con TIR anual | Resultado | Dif. TIR
   en `/dashboard/cartera`, para la ventana de período elegida.
   Simplificación declarada en `benchmark.ts`: sin `detectarRatiosNoDeclarados`
   (el aviso en pantalla de un split todavía no declarado en `AJUSTES_RATIO`).
   Núcleo financiero de Rendimientos completo. Queda para hito 7+: métricas
   de riesgo (Sortino/alfa/volatilidad), gráfico histórico completo, vistas
   ARS/MEP/CCL intercambiables.
   Simplificaciones declaradas en el código de `rendimiento.ts`: el tope
   de "caja insuficiente = aporte implícito" es por pool global, no por
   cuenta como el original; sin liquidación T+n; sin la distinción "cuenta
   importada completa" que desactiva ese tope en el legado.
6. **Importadores de bróker** — pendiente. Carga masiva desde CSV de
   Balanz, IEB+, Puente y Cocos, arrancando por el que más uso tenga.

### Hito 7+ — paridad completa con Cartera (sin priorizar todavía)

Todo lo que Cartera legado tiene y cartera-app todavía no, relevado el
2026-08-11. Se prioriza según lo que el usuario más use, no en el orden
en que está escrito acá:

- Métricas de riesgo: Sortino, alfa de Jensen, volatilidad, Sharpe (§10).
- Reconstrucción de NAV histórico (`reconstruirHistorialSnapshots`, §11)
  y el gráfico de evolución de cartera en el tiempo.
- Vistas ARS / MEP / CCL intercambiables (§8) — hoy cartera-app solo
  muestra ARS y USD MEP fijos.
- Panel Macro (dólares, commodities, tasas).
- Formulario de precios manuales en la UI (la tabla `precios_manuales`
  ya existe en el esquema; falta la pantalla para cargarlos).
- Saldos declarados por cuenta y liquidación T+n de la caja (mencionado
  como simplificación pendiente en el hito 1; la tabla `saldos` ya
  existe). **Al portarlo, ver §6 regla 13**: el legado tuvo un bug real
  ahí (ajuste dinámico que cancelaba movimientos posteriores) — diseñar
  cartera-app con un ajuste fijo desde el principio, no repetir el patrón
  viejo y tener que migrarlo después.
- Principales contribuidores/detractores, tabla de retorno por activo.
- Identidad visual (§17) y fondo NASA (§13) — hoy cartera-app es
  funcional pero visualmente básico.
- Diagnósticos en pantalla (brechas de datos, sobreventas, etc.).

### Qué significa "terminado"

cartera-app no se considera terminado mientras falte algo de esta lista,
salvo que el usuario decida explícitamente excluirlo (y en ese caso se
anota acá el motivo, no se borra en silencio — mismo criterio que "un
dato faltante se declara" de §1). Cada hito nuevo que se complete se
marca ✅ con fecha y referencia al PR, igual que el hito 1.
