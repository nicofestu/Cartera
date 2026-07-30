# Cartera — principios de diseño y contexto operativo

Documento único. Se lee **antes** de proponer o implementar cualquier cambio.
Reemplaza a `PRINCIPIOS.md` y `PROYECTO_CARTERA_CONTEXTO_E_INSTRUCCIONES.md`
como archivos separados: este es el único.

Última revisión: 2026-07-30.

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

## 1. Principio rector: escalar, no adaptar

**Esta aplicación se construye para servir a cualquier cartera, no a una en
particular.** Es el criterio que gana cuando hay conflicto con otros.

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

## 5. Decisión: cómo se mide el benchmark

### Estado anterior

El benchmark contra S&P 500 y Nasdaq 100 combinaba dos fuentes de distinta
naturaleza: para el pasado, los cierres oficiales del índice (FRED) en
`historial/indices.json`; para hoy, el precio del CEDEAR convertido a
"puntos de índice" mediante un **factor de calibración fijo** (`SPY_K`,
`QQQ_K`), retocado a mano cada tanto.

### Qué falló

El 2026-07-30 el S&P 500 cerró **+1,66%** y la app mostró el índice
**−0,79%** en el período "Hoy". Dos errores sumados:

1. `indices.json` se edita a mano y estaba atrasado cuatro ruedas. La
   búsqueda de nivel no distingue "ese día el mercado estuvo cerrado" de
   "ese día todavía no lo cargué": devolvía el último cierre que tuviera. La
   base terminó siendo un cierre de cuatro días antes.
2. El factor de calibración estaba desactualizado, y eso agrega un retorno
   inventado que no depende del mercado sino de cuándo se calibró.

### La evidencia que ordena el diagnóstico

Medido el 2026-07-30 sobre el CEDEAR SPY en dólares contra el S&P 500:

| ventana | CEDEAR | índice | diferencia |
|---|---|---|---|
| 4,53 años (2022-01-18 → 2026-07-29) | +59,33% | +59,84% | **−0,07% anual** |

**No hay deriva sistemática entre el CEDEAR y el índice.** El dividendo no la
produce: el S&P 500 que reporta la prensa es un índice de precio y también lo
excluye, igual que el precio del ETF, que cae en la fecha ex.

Lo que sí hay es **ruido**: la relación CEDEAR↔índice oscila con desvío diario
de 0,32% en condiciones normales y 1,18% mirando toda la serie, con episodios
de distorsión cambiaria real (octubre 2023). Un factor fijo **congela el
ruido del día en que se calibró** y lo arrastra para siempre a toda ventana
corta. Ese, y no la deriva, es el defecto de fondo.

### Decisión

**El benchmark se mide con la serie de retornos del CEDEAR. No se convierte a
puntos de índice mediante ningún factor calibrado a mano.**

- La serie del benchmark se construye **encadenando variaciones**, no
  niveles. Cada día aporta su retorno; nunca se compara un precio de una
  fuente contra un precio de otra.
- Donde el CEDEAR no tiene cobertura, se **empalma la serie oficial del
  índice por retorno**, no por nivel. Así conviven las dos fuentes sin
  necesidad de un factor de conversión: un cambio de escala no altera un
  retorno.
- Los dividendos del ETF se componen en la fecha ex, desde
  `historial/dividendos.json`.
- El **nivel** que se muestre, si se muestra alguno, se ancla al cierre
  oficial del índice en la primera fecha común. Es cosmético y no interviene
  en ningún retorno.
- El gráfico y las cards leen **la misma función**. Nunca dos maneras de
  medir lo mismo: ya ocurrió antes y llegaron a dar signos opuestos (ver
  también §11, la corrección del 28/07 sobre este mismo punto).

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

Mostraba **niveles** de índices y commodities derivados del mismo tipo de
factor calibrado a mano. Al 2026-07-30 estaban desviados hasta 2% (oro).
Decisión: **mostrar solo la variación porcentual, sin nivel.** Un número de
display equivocado sigue siendo un número equivocado.

### `historial/indices.json` — formato y quién lo escribe

Contiene las series diarias de cierre de S&P 500 y Nasdaq 100 (fuente FRED)
más los factores de calibración de respaldo. Formato comprimido:

```json
{ "sp500": { "b": "2022-01-03", "g": "1111311114…", "v": [4796.56, 4793.54, …] },
  "ndx":   { … },
  "calibracion": { "SPY_K": 577.0, "QQQ_K": 787.7, "MACRO_K": { "sp": 577.0, … } } }
```

`b` = fecha del primer cierre, `v` = valores, `g` = huecos en días entre
cierres consecutivos (un dígito por hueco). Lo expande `expandirSerie()`.

**El Action no lo toca**: `snapshot_historial.py` solo escribe
`historial/{año}.json`. **`indices.json` se edita a mano** y por eso se
atrasa — el diseño tiene que asumir que va a estar atrasado, no confiar en
que no lo esté (ver arriba, "qué falló").

Carga: `cargarBenchmarks()`, asíncrona y memoizada. Arranca vacía;
`nivelEn()` devuelve `null` cuando no hay serie, así que hasta que termine la
descarga la app funciona igual y simplemente no dibuja la línea del índice.

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
