# Cartera — principios de diseño y contexto operativo

Documento único. Se lee **antes** de proponer o implementar cualquier cambio.
Reemplaza a `PRINCIPIOS.md` y `PROYECTO_CARTERA_CONTEXTO_E_INSTRUCCIONES.md`
como archivos separados: este es el único.

Última revisión: 2026-08-14 (noche, sesión larga) — **Rediseño de Inicio +
P&L realizado por período + fix de CCL + independencia total de datos
históricos.** Arrancó como un pedido de UI (achicar la card de NAV) y
terminó destapando y arreglando tres cosas de fondo: un bug real de CCL en
el cálculo de caja, snapshots históricos migrados del legado con un motor
de cálculo distinto al de cartera-app, y una dependencia completa del repo
legado + argentinadatos.com para cualquier precio o dólar pasado. Commits
directos a `main` (autorizado, sin usuarios activos). Se abre acá el
detalle completo; las secciones de abajo (§8, §23, §26) quedan
actualizadas con el estado final.

**1) Inicio — NAV vuelve a ser chico, nuevas cards.** A pedido de Nicolás
viendo la app en vivo: el NAV pasa de `CardHero` (grande, con MEP/CCL al
lado sin importar la vista elegida) a una `Card` chica, mostrando SOLO la
moneda seleccionada. Se sacó "P&L no realizado" de Inicio. Se agregaron 3
cards de "Liquidez" (ARS/MEP/CCL por pool, cada una convertida a la vista
elegida — `montoArsAVista()`, nuevo helper) y N cards de "Posición por
cuenta" (NAV por cuenta, dinámico — Set de cuentas, no una lista fija de
2, pensado para escalar).

**2) P&L no realizado + realizado, Capital aportado/retirado — a
Rendimientos → Retorno.** No realizado se mudó tal cual (sigue siendo "a
hoy", no depende del período). Realizado es NUEVO para todos los
períodos, no solo "Todo": se portó `remarcarAMercado()`/
`realizadoEnPeriodo()` del legado a `lib/cartera/realizado.ts` — sin esto,
vender en la ventana algo comprado antes le sumaba a "esta ventana" toda
la ganancia vieja (el bug que el legado mismo advierte evitar). El caso
"Todo" no necesita remarcado — sale gratis de `derivarPosiciones()`
(`realARS`/`realUSD`, ya lo calculaba puertas adentro, solo se expuso en
`nav.ts`). Validado con datos reales: para "mensual", el número correcto
dio $613.931 ARS contra $1.153.028 del cálculo naive (resta de
acumulados) — casi el doble, confirma que el remarcado hace trabajo real,
no cosmético. Capital aportado/retirado: dos cards nuevas, cross-
convertidas a la vista — `ultimoHito.apor`/`.ret` ya los calculaba
`construirHitosCaja()`, solo se expusieron.

**2 bis) El fetch de precios para remarcar resultó mucho más barato de lo
que parecía.** La primera reacción fue "necesita fetch de precios
históricos en cada carga de Rendimientos, no lo hagamos" — pero remarcar
solo necesita el precio de UNA fecha puntual (el arranque del período),
no todo el historial de la cartera como sí necesita "Reconstruir
historial" — alcanza con 1-2 años de `historial/{año}.json`
(`fetchPreciosParaRemarcado`, acotado). Con el backfill del punto 4, ni
siquiera eso: sale de la tabla propia.

**3) CCL — bug real encontrado y arreglado, en dos lugares.**
`cajaARS` (`nav.ts`) usaba el dólar MEP para el pool CCL en vez del CCL
real — mismo bug en la valuación de cauciones pooleadas en CCL (`nav.ts`
y `historial.ts`), que tampoco miraba `c.pool`. Con las tasas reales del
día (MEP $1.518, CCL $1.574 — 3,7% de spread), el impacto en tu saldo
actual del pool CCL fue chico (está casi en cero), pero el bug era real y
generalizable a cualquier usuario con más saldo ahí. Arreglado en
`nav.ts` (cajaARS + cauciones) — `historial.ts` (reconstrucción de
cierres pasados) en su momento se dejó igual "a propósito, no existe CCL
histórico" — ver punto 4, esa premisa resultó estar desactualizada.

**4) Independencia de datos históricos — proyecto grande, a pedido de
Nicolás ("que no dependa de nada externo").** Hasta acá cartera-app
recalculaba TODO contra el repo legado (`historial/{año}.json`,
`datos/precios/on-{c,d}.json`) y contra argentinadatos.com en vivo, en
cada reconstrucción o remarcado. Ahora:
- **Backfill único** (2026-08-14): 1.129 fechas de precios
  (bono/letra/on/accion/cedear, 2022-01-03 a hoy) migradas del repo
  legado a `public.precios_mercado_diarios` (mismo formato que ya usaba
  el cron nuevo, cero esquema nuevo); ~5.000 fechas de MEP/CCL
  (2013/2018 a hoy) a `public.dolares_diarios` (tabla nueva, ver
  `supabase/schema.sql`).
- **`lib/cartera/historial.ts` reescrito**: `fetchHistorialPrecios`/
  `fetchMepHistorico`/`fetchCclHistorico` consultan la tabla propia
  PRIMERO; solo caen al fetch externo (legado/argentinadatos) si la
  tabla no tiene nada para el rango pedido — la dependencia externa
  queda como red de seguridad, no como camino principal.
- **Hallazgo real durante el backfill, CORRIGE una nota anterior de este
  mismo documento (§8, más abajo)**: "CCL histórico no existe" era
  información vieja, nunca vuelta a chequear — argentinadatos.com SÍ
  tiene una serie de CCL (casa `contadoconliqui`), con MÁS cobertura que
  el MEP que ya se usaba (2013 vs. 2018) y sin huecos donde MEP sí tiene
  dato. Este hallazgo es lo que hizo posible el punto 3.
- **Cron de precios de mercado, arreglado**: existía desde hace ~2
  semanas (`app/api/cron/precios-mercado/route.ts`, programado en
  `vercel.json`) pero nunca había escrito una sola fila —
  `precios_mercado_diarios` estaba en cero pese a estar todo bien
  armado en el código. Diagnosticado en vivo con Nicolás mirando Vercel
  (plan Hobby: logs de solo 1 hora de retención, así que revisar hacia
  atrás no servía — hubo que disparar una corrida y mirar en caliente).
  Un trigger manual devolvió 200 con datos reales completos (bono 185,
  letra 25, on 627, acción 95, cedear 941, FCI 3.680 fondos) y quedó
  confirmado que la corrida programada de esa tarde también escribió
  sola, sin intervención — el cron ya está andando. La causa raíz de por
  qué no había corrido antes queda sin confirmar (no se encontró ningún
  error concreto; lo más probable es algún deploy anterior que no llegó
  a registrar bien el cron nuevo en el scheduler de Vercel). De paso, el
  cron ahora TAMBIÉN guarda el MEP/CCL del día en `dolares_diarios`
  (antes solo guardaba precios de activos). Recordatorio en el calendario
  de Nicolás para el martes 18/8 18:55 ART (movido del lunes por
  feriado) para confirmar que la corrida del lunes 17 (feriado, el cron
  no sabe de feriados argentinos) y la del martes salieron solas.

**5) Snapshots históricos — backup, borrado y reconstrucción con el motor
nuevo.** Al armar el punto 3, se encontró que los 104 snapshots
guardados NO eran el cálculo propio de cartera-app: eran una migración en
bloque desde el gist del legado (`importar-legado`, hito 4 — mismo
`created_at` exacto en los 104), calculados con el motor VIEJO (caja en
un solo pool, sin por-cuenta ni tope de compra ni liquidación T+n). La
diferencia contra recalcular con el motor propio llegó a $100K+ ARS por
día — no por CCL (que en tu historial estuvo casi siempre en cero), sino
porque son dos motores de cálculo distintos. Backup completo entregado
como archivo (104 filas, JSON) antes de tocar nada; los 104 se borraron
de `snapshots`; Nicolás disparó "Reconstruir historial hacia atrás" con
el motor de cartera-app — resultado: **89 filas** (15 quedaron sin
snapshot, declaradas incompletas — muy probablemente por un hueco de
cobertura de un FCI puntual, ver §26bis para el detalle completo de la
investigación). No es una regresión: es la primera vez que esas fechas
pasan por la validación real de cobertura, en vez de heredar el cálculo
del legado sin chequeo.

**Validación de toda la sesión:** `tsc --noEmit --strict` sobre el
proyecto completo en cada entrega (0 errores al final, con al menos un
error real encontrado y corregido en el camino — `Set<string>` mal
inferido), confirmado con prueba negativa (inyectar un error de tipos a
propósito) en cada PR. Smoke tests con datos y precios REALES de
producción (vía Supabase + argentinadatos.com, no simulados): identidad
"suma de las 3 cards de Liquidez == cajaARS", "suma de navPorCuentaARS ==
navARS", comparación remarcado-vs-naive del P&L realizado, coincidencia
exacta entre el `realARS` nuevo (vía `realizadoEnPeriodo(null,...)`) y el
`nav.realARS` ya validado. Diagnóstico del cron de precios de mercado
hecho EN VIVO con Nicolás mirando el dashboard de Vercel — no
especulación desde el código solo.

Última revisión: 2026-08-14 (tarde-noche) — **Plan de mejoras UX/UI de
Claude Design, cartera-app: los 11 puntos entregados en 4 PRs, commit
directo a `main` (autorizado por Nicolás, sin usuarios activos aún).**
Fuente: `Plan de mejoras UX-UI - Cartera.md` (subido por Nicolás) +
prototipo `Cartera Rediseño.dc.html`, ambos en project knowledge. Ningún
cambio tocó cálculos financieros (§6 regla 12) — los 4 PRs son
estructura/estilo/interacción puros.

- **PR1** (`9e04c2c`…`079c533`, 5 archivos): fondo de tabla sólido —
  las ~11 tablas de la app se renderizaban como `<table>` sin envoltorio
  opaco, así que el fondo NASA fijo se veía a través de las celdas
  (`.th-legado` ya tenía `background:transparent` sin nada opaco detrás);
  NAV pasa a `CardHero` (el componente existía en `ui.tsx` desde el hito
  7+ pero nunca se había usado en ninguna pantalla); color por cuenta
  (`claseCuenta()` en `ui.tsx`, Puente azul / Galicia ámbar, match de
  texto normalizado, no un enum — ver lib/cartera/cuentas.ts); selector
  de moneda ARS/MEP/CCL siempre visible en `TabBar.tsx` (antes
  desaparecía fuera de `/dashboard/cartera`); `--text-tertiary` subido de
  `#626b77` a `#7a838a` — el original daba ~3,5:1 de contraste contra
  `--bg-elevated-2`, por debajo del mínimo WCAG AA (4.5:1).
- **PR2** (`f7a9184`…`505e0b0`, 8 archivos, 2 nuevos): `InfoTip` pasa de
  `title=` nativo a `<details>/<summary>` — en mobile, `title=` no se
  dispara de forma confiable con un tap, así que los tooltips quedaban
  decorativos; sigue siendo Server Component, sin JS de cliente. Los dos
  gráficos (`nav-chart.tsx`, `rendimiento-chart.tsx`) pasan a
  `"use client"` y agregan hover/touch con línea guía + tooltip
  fecha/valor (antes eran 100% server-rendered, sin ninguna
  interactividad). Nuevo `components/ConfirmDelete.tsx`: borrado en 2
  pasos ("¿Confirmar? Sí/No" inline en la fila) para movimiento, caución
  y precio manual — antes "Borrar" ejecutaba de un clic. Nuevo
  `app/dashboard/movimientos/historial-table.tsx`: filtros de texto
  libre + chips de tipo de operación (multi-selección, solo se muestran
  los tipos presentes en los datos) + selector de cuenta + contador de
  resultados.
- **PR3** (`77a56c3`, `b924305`): "Rendimientos" se divide en sub-pestañas
  Retorno / Comparativa / Riesgo. Mismo patrón sin re-fetch que
  `Seccion.tsx` (ver más abajo, "patrón de sub-pestañas"). El selector de
  período y la sub-pestaña activa se preservan mutuamente en la URL.
- **PR4** (`063dc89`, `c744aba`, `bcf1834`): "Movimientos" se divide en
  Historial / Importar / Precios manuales. **Los botones globales
  "+ Movimiento" / "Saldos" (`components/AccesoRapido.tsx`, en el header
  vía `TabBar.tsx`) NO se tocaron** — decisión explícita de Nicolás,
  confirmada dos veces en la misma sesión: quedan donde están, no se
  agregan a ninguna sub-pestaña ni se duplican. Ver "Acceso rápido a
  Movimientos y Saldos" en §26 (hito 7+): ya estaba resuelto de una
  sesión anterior no documentada acá — este documento seguía diciendo
  "pendiente" mientras el código ya lo tenía hecho (mismo patrón de
  "documentación atrasada" que el hallazgo 1 de más abajo).
  **Bug real encontrado y corregido antes de subir** (no llegó a
  producción): el primer diseño de esta sub-pestaña hacía que
  `?error=` en la URL seleccionara automáticamente "Precios manuales" —
  pero `crearMovimiento`/`crearCaucion` (Server Actions del modal global
  "+ Movimiento") **también** redirigen con `?error=` a esta misma
  ruta, así que un error de esas dos acciones habría aterrizado al
  usuario en la sub-pestaña equivocada. Arreglo: `precio-actions.ts`
  pide `?mtab=precios` explícito en sus propios 3 redirects, en vez de
  que la pantalla lo infiera; se mantiene además un banner de error
  genérico visible en cualquier sub-pestaña, para que ningún error quede
  invisible sin importar qué acción lo generó.

**Patrón de sub-pestañas (nuevo, establecido en PR3 y PR4, reusable a
futuro):** `?param=` en la URL + un Client Component chico que lee
`useSearchParams()` y alterna `display:none` — el contenido de TODAS las
sub-pestañas ya lo calculó el Server Component en la misma pasada, así
que cambiar de sub-pestaña no repite ningún fetch a Supabase/data912/
FRED. Tres instancias hoy: `components/Seccion.tsx` (`?tab=`, Inicio ⇄
Rendimientos, preexistente), `components/SubTabRendimiento.tsx`
(`?rtab=`, Retorno/Comparativa/Riesgo), `components/SubTabMovimientos.tsx`
(`?mtab=`, Historial/Importar/Precios manuales). **Lección del bug de
arriba, para la próxima sub-pestaña que se agregue:** si una Server
Action necesita aterrizar en una sub-pestaña puntual, tiene que pedirlo
con el query param explícito en su propio `redirect()` — nunca inferirlo
en la pantalla a partir de otro parámetro (como `?error=`) que puede
venir de más de una acción distinta.

**Validación de los 4 PRs:** `tsc --noEmit --strict` sobre el proyecto
COMPLETO (con `npm install` real) en cada uno — encontró errores reales
de tipos en PR2 (`Set<string>` mal inferido en el filtro de chips) y PR3
(`rtab` faltante en el tipo de `searchParams`), corregidos antes de
subir; los 4 PRs terminaron en cero errores, confirmado además con una
prueba negativa (inyectar un error de tipos a propósito) en cada uno.
Smoke tests de lógica pura donde aplicaba: `claseCuenta()` con
mayúsculas/tildes/cuentas desconocidas; filtrado combinado de Historial
(texto + tipo + cuenta, con exclusión correcta de las patas de una
caución); cálculo de "punto más cercano" del hover en los gráficos, en
distintas escalas de contenedor; matching de SPY por fecha más cercana;
construcción de URLs `hrefRtab`/`hrefMtab`/`hrefPeriodo` preservando
todos los parámetros combinados. Para las reestructuraciones de JSX (PR3,
PR4): control por conteo de piezas clave entre la versión en `main` antes
del cambio y la versión reestructurada (cada `InfoTip`, cada tabla, cada
componente reutilizado) para confirmar que nada se perdió ni se duplicó
al mover el árbol. **Sin prueba en navegador** (Playwright no funciona en
este sandbox) — pendiente que Nicolás confirme en vivo, en particular el
*feel* táctil del hover de los gráficos y el tap de los tooltips en
mobile, que por su naturaleza no se puede validar por fuera del
navegador real.

Última revisión: 2026-08-14 (noche) — **arreglo de la discrepancia de
rendimiento CONFIRMADO EN VIVO, en las dos apps, al mismo momento.**
Nicolás subió los 3 archivos entregados (pegándolos en GitHub — 3 commits
directos a `main`: `c83b98a`, `8f57d4c`, `51fd952`). Verificado con
`git diff` contra el commit local que no se pudo pushear (`4e46347`):
contenido idéntico salvo una línea en blanco final que el editor web de
GitHub recorta — la subida fue exacta. Vercel redeployó solo.

Comparación en vivo, misma sesión de navegador, mismo momento (NAV a los
pocos segundos de diferencia, $12.236.468 cartera-app vs. $12.223.478
legado — la diferencia es timing de precios, no el fix):

| Métrica (ARS, "Todo") | Legado | cartera-app (post-fix) | cartera-app (pre-fix, mañana) |
|---|---|---|---|
| Retorno total | +33,40% | **+34,5%** | +39,2% |
| TIR anual | +135,44% | **+141,2%** | +168,2% |
| Capital aportado | $14.175.414 | (no expuesto en UI) | $13.654.116 (~3,7% menos) |

La brecha de retorno pasó de 7,2pp a **1,1pp**; la de TIR, de 39pp a
**5,8pp**. Confirma en el navegador real (no solo smoke test) que el
arreglo (caja por cuenta + `cuentas_importadas` en `construirHitosCaja()`)
funcionó y va en la dirección y magnitud predichas por el smoke test de la
tarde (que había dado 33,19% vs. 32,00% del legado, sobre datos de un
momento algo anterior). La brecha residual (~1-6pp) no se investigó más:
es candidata a la simplificación que sigue declarada (sin liquidación
T+n, ver `rendimiento.ts` y §26 hito 5) o a timing entre las dos lecturas
— no se concluye cuál sin evidencia adicional.

**Tipo de validación, para que quede explícito (§15):** esto SÍ es prueba
real en navegador — se abrieron ambas apps, ya autenticadas, y se leyó el
DOM con Claude en Chrome. Distinto del smoke test de Python de la tarde
(reimplementación, no el código real) y del `tsc --noEmit` (sintáctico +
tipos, no ejecución).

Última revisión: 2026-08-14 (más tarde, mismo día) — arreglo de la
discrepancia de rendimiento (ver entrada anterior) **implementado y
validado, pero NO subido a `main`.** Nicolás autorizó explícitamente
commit directo a `main` (sin PR/preview). Se portó a `lib/cartera/
rendimiento.ts` el mismo patrón que ya existía en `calcularCajaNativa()`
(`caja.ts`, hito 7): caja por CUENTA en vez de pool global, más respeto del
flag `cuentas_importadas` (cuentas con historial completo, sin tope de
compra) — resuelve las simplificaciones #1 y #3 que el propio archivo
declaraba. `serieRendimiento`/`serieDiaria`/`construirHitosCaja` pasan a
recibir `cuentasLibres: Set<string>`; `nav.ts` lo expone en `ResultadoNav`
(ya lo calculaba internamente para `calcularCajaNativa`, solo faltaba
reexponerlo); `page.tsx` pasa `nav.cuentasLibres` en las tres llamadas.

Validación, distinguiendo cada tipo (no se probó en navegador — no hay
Playwright en el sandbox, ver §15/§23.7):

- **Sintáctica:** `tsc --noEmit` sobre el proyecto COMPLETO (`npm install`
  sí funcionó en este sandbox, a diferencia de sesiones anteriores) — cero
  errores, incluye resolución de tipos real, no solo parseo.
- **Smoke test de lógica:** reimplementación en Python del algoritmo nuevo
  (por cuenta + `cuentasLibres`) contra los datos reales de Supabase,
  comparada contra la reimplementación del algoritmo viejo (pool global).
  Resultado: viejo da 38,17% ARS (consistente con el ≈39,2% que muestra la
  app en vivo); nuevo da **33,19% ARS — mucho más cerca del 32,00% del
  legado**, con la brecha restante (~1,2pp) explicable por timing de
  precios en vivo entre auditorías, no por la caja. El smoke test detecta
  explícitamente los 3 casos de aporte implícito en la cuenta Galicia
  (02/07, 16/07, 31/07) que el algoritmo viejo NO detectaba y el nuevo sí —
  el control que exige §15 (demostrar que la versión vieja fallaba en el
  caso que se dice arreglar).
- **NO se ejecutó el TypeScript real** (el smoke test es una reimplementación
  fiel en Python, no el código que se entrega) y **NO hay prueba en
  navegador**.

**Por qué no se subió a `main` pese a la autorización explícita:** el
commit local se creó sin problema (`git commit`, hash `4e46347`, sobre
`main` actualizado a `b055564`), pero `git push origin main` fue
rechazado por el proxy de git del sandbox: *"access denied by the git
proxy: nicofestu/cartera-app is not in this session's authorized
repository set"* — mismo mensaje (con otra redacción) que ya había
bloqueado `api.github.com` en la auditoría de la mañana. Confirmado que
es una restricción de ESCRITURA específicamente: `git fetch`/`git clone`
con el mismo token embebido en la URL funcionan sin problema (así se bajó
el repo), y se probó también pushear a una rama nueva (no solo `main`) con
el mismo resultado — es un bloqueo a nivel de repo completo, no de rama.
No hay ninguna tool tipo `add_repo` disponible en esta sesión para pedir
acceso de escritura. **Entrega real: los 3 archivos completos
modificados (`rendimiento.ts`, `nav.ts`, `page.tsx`) más un patch de git
(`git format-patch`), enviados a Nicolás para que los aplique o pegue él
mismo** — mismo criterio que "si no hay token disponible, entregar el
archivo completo" de §16/§23, aplicado acá porque el token, aunque
disponible, no alcanza por la restricción del sandbox, no por falta de
permisos del token en sí.

**Nota para sesiones futuras (ver también §24):** en este sandbox, un PAT
de GitHub embebido en la URL de un remoto git permite `clone`/`fetch` de
un repo privado, pero NO permite `push` — el proxy de red del entorno lo
bloquea a nivel de sesión, independientemente de los permisos del token.
No vale la pena reintentar `git push` de otras formas (otra rama, otro
remote, `gh` CLI — que además pasa por `api.github.com`, bloqueado
también) esperando que alguna funcione: hay que asumir de entrada que un
commit directo, aunque el usuario lo autorice, se entrega como archivo(s)
completo(s) + patch, salvo que aparezca una tool nueva para pedir acceso
de escritura al repo.

Última revisión: 2026-08-14 — auditoría comparativa Cartera vs cartera-app
con datos reales en vivo (ambas apps abiertas con la sesión de Nicolás),
más lectura directa del código de los dos repos (no de memoria: este mismo
documento estaba desactualizado, ver más abajo). Informe completo en
project knowledge, `claude/auditoria-cartera-vs-cartera-app-2026-08-14.md`.
Cuatro hallazgos:

1. **Documentación atrasada.** Este documento quedó congelado a media
   tarde/noche del 2026-08-13, pero el repo real tiene ~35 commits más esa
   misma noche (hasta las 22:45) que cierran trabajo real y no habían
   quedado anotados acá. Se corrige en §26 más abajo.
2. **Discrepancia real de rendimiento — CAUSA IDENTIFICADA, falta portar el
   arreglo. Prioridad alta.** Con los mismos datos, mismo instante: Retorno
   Total "Todo" ARS +32,00% en el legado vs. +39,2% en cartera-app; TIR
   anual +129,19% vs. +168,2%. El NAV y el P&L no realizado coinciden casi
   exacto entre las dos apps, así que no es un problema de valuación.
   Diagnóstico con acceso real a `snapshots` y `movimientos` (vía API REST
   de Supabase, service_role — ver nota de infraestructura en §24):
   reimplementar `construirHitosCaja`/`serieDiaria`/`retornoEntre` en Python
   sobre los datos reales de Nicolás reprodujo el número que muestra la app
   (≈38-39%, contra el 32% del legado) casi exacto — **descarta un bug en
   la fórmula portada**, la lógica está bien traducida. La causa está en la
   simplificación #1 ya declarada arriba en `rendimiento.ts`: el aporte
   implícito de una compra se detecta contra la caja del POOL global (ARS/
   USD de toda la cartera), no contra la caja de la CUENTA donde ocurre la
   compra, como sí hace el legado. Confirmado con los datos reales: la
   cuenta Galicia nunca recibió un depósito propio antes del 2026-08-12 (los
   6 depósitos de la cartera fueron casi todos a Puente), pero tiene
   posiciones reales (VIST) — esas compras se financiaron con caja de Puente
   a través del pool compartido, así que cartera-app las clasifica como
   "rotación interna" en vez de aporte externo a Galicia. Efecto medible:
   el "capital aportado" acumulado que reconstruye cartera-app da
   ≈$13.654.116 contra los $14.175.414 que muestra el legado — un
   denominador ~3,7% más chico explica buena parte (aunque probablemente no
   toda) de la diferencia en el % y, sobre todo, en la TIR, que es mucho más
   sensible al tamaño y momento de cada aporte. Arreglo: portar la detección
   de aporte implícito a nivel de cuenta (no de pool), tal como ya estaba
   anotado como pendiente en el comentario de `rendimiento.ts` — no hace
   falta rediseñar nada, es extender la lógica existente. Herramienta usada
   para el diagnóstico: script Python ad hoc (no forma parte del repo,
   descartado al cerrar la sesión) que reimplementa las funciones de
   `rendimiento.ts` línea por línea contra los datos reales vía la API REST
   de Supabase — reproducible en cualquier sesión con la service_role key.
3. **Navegación: sin acceso rápido a Movimientos/Saldos.** El legado tiene
   dos botones globales en el header (`+ MOVIMIENTO`, `SALDOS`), accesibles
   con un clic desde cualquier pestaña, que abren un modal. cartera-app no
   tiene acceso global: hay que entrar a la pestaña Movimientos y recorrer
   una página larga (Nuevo movimiento → Nueva caución → Declarar saldo →
   Precio manual → Posiciones → Registro de operaciones) — "Declarar saldo"
   en particular queda a mitad de camino, sin ningún atajo desde otras
   pestañas.
5. **Nota de datos, no de la auditoría en sí:** al consultar `movimientos`
   para el diagnóstico de arriba aparecieron 3 filas `op="ajuste"`, ticker
   "AJUSTE SALDO", cuenta Puente, creadas el 2026-08-14 a las 01:56 UTC
   (ARS −17.276,83 · USD MEP +38,41 · USD CCL −38,41) — no fueron
   insertadas por esta sesión (el flujo de "Declarar saldo" es un Server
   Action que solo se dispara al enviar el formulario, y esta sesión no
   completó ni envió ese formulario en ningún momento, solo navegó y
   scrolleó). Quedan anotadas acá por transparencia; si Nicolás no las
   generó él mismo en paralelo, vale la pena que las revise en
   `/dashboard/movimientos` (se pueden borrar como cualquier movimiento).

4. **Estética: brecha visual mayormente cerrada, quedan dos diferencias.**
   La tanda de commits del 13/8 ("portar X del legado") ya igualó paleta,
   tipografía, tabs, fondo NASA, cards, tablas, estados vacíos y
   transiciones — en las capturas en vivo ambas apps se ven casi idénticas.
   Lo que sigue distinto: (a) cartera-app no tiene header persistente
   (título/timestamp/botones de acción visibles siempre, como en el
   legado); (b) el mini-gráfico de Inicio en cartera-app muestra el NAV
   absoluto en pesos, mientras que el del legado en esa misma posición
   muestra el % de rendimiento time-weighted (que en cartera-app existe,
   pero solo en la pestaña Rendimientos).

Última revisión: 2026-08-13 — hito 7+ en §26: cuatro entregas sobre
cartera-app. (1) Vistas ARS/MEP/CCL intercambiables (PR #7, merge
`e9d84af`). (2) Saldos declarados por cuenta + liquidación T+n de la caja,
rediseñado a mitad de camino: la primera versión guardaba un delta FIJO
en una tabla aparte (`saldos`) y en producción se vio en vivo que un
delta migrado del historial viejo quedaba desactualizado e inflaba el
NAV — mismo bug de fondo que §6 regla 13, aunque el diseño ya lo evitaba
en el flujo normal. Se reemplazó por un movimiento real (`op="ajuste"`)
calculado una sola vez al guardar, sin delta que se pueda desactualizar
(PR #6). De paso se corrigió un bug de dedupe real (acento en "DEPÓSITO"
vs "DEPOSITO" duplicaba movimientos migrados del gist) y se limpiaron
datos de producción afectados. (3) Formulario de precios manuales en la
UI (PR #8, merge `e0d9de2`) — la tabla y el cálculo ya existían, faltaba
la pantalla. (4) Reconstrucción de NAV histórico
(`reconstruirHistorialSnapshots`, puerto acotado sin la lógica de reparar
snapshots viejos, que no aplica acá) + gráfico de evolución de cartera —
primero se agregó un gráfico de NAV absoluto, y a pedido de Nicolás
(no se parecía al de la app vieja) se sumó además un gráfico de %
rendimiento time-weighted, con un test cruzado contra `retornoEntre` para
no repetir el bug de "dos fórmulas para el mismo concepto" de la regla 14
(PR #9, merge `476056a`). Además, PR #10 abierto (contribuidores/
detractores + tabla de retorno por activo, solo posiciones abiertas hoy)
esperando confirmación del preview.

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

**Nota 2026-08-14 (cartera-app, múltiples `page.tsx`):** cuando se entrega
un archivo cuyo NOMBRE se repite en varias carpetas del repo (cartera-app
tiene varios `page.tsx`: `app/page.tsx` de 12 líneas, `app/dashboard/
cartera/page.tsx` de 1167, etc.), decir siempre la RUTA COMPLETA al
entregarlo, no solo el nombre — el usuario puede terminar comparando o
editando el archivo equivocado si dos archivos comparten nombre.

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
15. **El mismo concepto entre APPS tampoco puede dar dos números
    distintos, y eso también hay que chequearlo con datos reales, no solo
    leyendo el código.** Auditoría 2026-08-14: Retorno Total "Todo" ARS
    daba +32,00% en Cartera legado y +39,2% en cartera-app con los mismos
    datos reales (TIR anual +129,19% vs. +168,2%) — el NAV y el P&L no
    realizado coincidían casi exacto. Diagnóstico confirmado reimplementando
    `construirHitosCaja`/`serieDiaria` en Python contra los datos reales
    (vía API REST de Supabase): la fórmula portada está bien — el número
    que reproduce coincide con lo que muestra cartera-app, no con el
    legado —, la causa es la simplificación #1 ya declarada en
    `rendimiento.ts`: el aporte implícito de una compra se detecta contra
    la caja del POOL global en vez de la caja de la CUENTA puntual, y esta
    cartera tiene una cuenta (Galicia) que nunca recibió depósito propio y
    se financió vía el pool compartido con otra cuenta (Puente) — el
    legado sí lo detecta como aporte externo a esa cuenta, cartera-app no.
    Ver §26 (hito 5) para el detalle completo y el arreglo pendiente.
    Lección: **una fórmula puede estar perfectamente bien portada y el
    resultado igual difiere, si una simplificación ya declarada tiene un
    efecto real en la cartera concreta que se está comparando** — no
    alcanza con revisar la fórmula, hay que correrla con datos reales y
    comparar el número final contra el legado. **Arreglo implementado,
    subido y CONFIRMADO EN VIVO el mismo día** (ver la entrada de "Última
    revisión" 2026-08-14 noche, arriba del todo, y §26 hito 5): portado el
    mismo criterio de `calcularCajaNativa()` (caja por cuenta + respeto de
    `cuentas_importadas`) a `construirHitosCaja()`. La brecha bajó de 7,2pp
    a 1,1pp de retorno (39pp a 5,8pp de TIR), verificado con las dos apps
    abiertas al mismo momento — no solo con el smoke test.
16. **Un archivo entregado por nombre, cuando el repo tiene varios con el
    mismo nombre, se confirma por ruta completa, no por nombre solo.**
    2026-08-14: cartera-app tiene múltiples `page.tsx` (`app/page.tsx`,
    12 líneas; `app/dashboard/cartera/page.tsx`, 1167 líneas; y otros).
    Al entregar uno, decir siempre la ruta completa desde la raíz del
    repo — ver §2.

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
el tipo de cambio al que entró cada peso— y no hay un campo `ccl` por
movimiento, análogo a `mep`. Valuar hoy a CCL y dividir por una base MEP
mete la brecha entre los dos dólares adentro del rendimiento como si fuera
resultado de la cartera.

Consecuencia buscada: los porcentajes de MEP y CCL son idénticos; los montos
absolutos no.

Si en algún momento se quiere un CCL histórico real **por movimiento**,
hace falta agregar un campo `ccl` a cada movimiento, análogo a `mep`. Es
un cambio grande: evaluar contra §18 (fuentes) antes de encararlo.

**Corrección 2026-08-14 (cartera-app):** este párrafo decía "no existe una
serie CCL histórica" — resultó ser información vieja, nunca vuelta a
chequear. argentinadatos.com sí tiene una serie diaria de CCL (casa
`contadoconliqui`), con MÁS cobertura que la de MEP que ya se usaba (2013
contra 2018) y sin huecos donde MEP sí tiene dato — cartera-app ya la usa
para valuar el pool de caja en CCL (`cajaARS` en `nav.ts`) y las
cauciones pooleadas en CCL, backfillada en `public.dolares_diarios` (ver
§26bis). Lo que sigue sin existir, y es la limitación real de este
párrafo, es la granularidad POR MOVIMIENTO: cada movimiento en dólares
sigue llevando solo `mep` (la cotización del día de esa operación
puntual), nunca `ccl` — así que el costo promedio de una posición, y por
lo tanto cualquier P&L contra ese costo, se sigue llevando en MEP nomás,
sin importar que la serie diaria de CCL ya esté disponible. La regla de
arriba (montos en la vista elegida, retornos siempre en base ARS/MEP)
sigue vigente tal cual — lo que cambió es que ya no depende de que "el
dato no existe": ahora es una decisión de diseño consciente, no una
limitación de datos.

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
**Excepción 2026-08-14: Claude en Chrome (`mcp__claude-in-chrome__*`) SÍ
está disponible en este entorno y permite abrir la app real (autenticada,
sesión del usuario) y leer el DOM — no es Playwright, pero es una prueba
real en navegador. Usarlo para confirmar en vivo un cambio de cálculo
después de que el usuario lo suba, cuando esté disponible.**

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
en ese contexto. **Salvedad real, 2026-08-14: si el sandbox bloquea el
push (ver §24), la entrega vuelve a ser archivo completo + patch, igual
que acá, aunque el usuario haya autorizado el commit directo — se le avisa
explícitamente que fue así, no se da a entender que se subió solo. En ese
caso, decir siempre la RUTA COMPLETA de cada archivo (§2, §6 regla 16),
no solo el nombre, para evitar que el usuario pegue en el archivo
equivocado si hay nombres repetidos en el repo.**

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

**Auditoría 2026-08-14 (cartera-app):** la sesión de portado del 13/8 (§26,
hito 7+) ya igualó paleta, tipografía (Archivo + Chivo Mono), tabs
subrayados, fondo NASA, cards, tablas, estados vacíos y transición fadeIn —
verificado en vivo, ambas apps se ven casi idénticas. Quedaban dos
diferencias abiertas, ambas resueltas o cerradas el mismo día más tarde:
(1) **header persistente estilo legado — decisión tomada: no se
construye** (Nicolás confirmó que el diseño actual, sin título/timestamp/
"..." fijos, es la decisión final — ver §26, hito 7+); (2) mini-gráfico de
Inicio en % en vez de NAV absoluto — **sigue sin tocar**, el Plan de
mejoras UX/UI de esta sesión no lo incluía (ver §26, hito 7+, para el
detalle).

**Plan de mejoras UX/UI (Claude Design) — ✅ hecho 2026-08-14 (tarde-
noche), 4 PRs.** Fondo de tabla sólido (antes se veía la foto NASA a
través de las celdas), NAV como card hero, color por cuenta (Puente
azul/Galicia ámbar), selector de moneda siempre visible, contraste WCAG
AA de texto terciario, tooltips reales (`<details>/<summary>`, tap en
mobile), hover/touch interactivo en los 2 gráficos de línea, borrado en 2
pasos, filtros de Historial, sub-pestañas dentro de Rendimientos
(Retorno/Comparativa/Riesgo) y dentro de Movimientos (Historial/Importar/
Precios manuales) — con un patrón de sub-pestañas nuevo y reusable
(`?param=` en la URL + toggle client-side sin re-fetch, ver la entrada de
"Última revisión" arriba del todo para el detalle completo y los
commits). Ningún cambio tocó cálculos financieros.

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
**Nota 2026-08-14: `api.github.com` está bloqueado para este repo en el
sandbox (ver §24) — el `sha` se puede obtener en cambio con
`git rev-parse HEAD:ruta/al/archivo` sobre un clone/fetch actualizado, que
sí funciona.**

**2. Cada archivo que se modifica se valida antes de subir, no después.**
Mínimo: chequeo sintáctico (parser de TypeScript/JSX — ver ejemplo real
usado para `route.ts`/`page.tsx`). Cuando el cambio toca lógica de datos
(queries a Supabase, RLS, Server Actions que escriben), preferir inspección
manual explícita de qué usuario puede leer/escribir qué fila, en vez de
asumir que el cliente ya filtra correctamente. **Nota 2026-08-14: `npm
install` sí funciona en este sandbox (a diferencia de lo asumido en
sesiones anteriores) — cuando el cambio toca varias funciones o firmas,
preferir `tsc --noEmit` sobre el proyecto completo (type-check real, no
solo parseo) en vez de solo parsear los archivos tocados.**

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
   **Nota 2026-08-14: "commitear directo a `main`" puede no ser posible
   literalmente desde este sandbox — ver §24, nota de infraestructura sobre
   el proxy de git. Verificar con un `git push` real antes de prometerlo;
   si falla, avisar y entregar archivo completo + patch en su lugar (con
   RUTA COMPLETA de cada archivo, ver §6 regla 16) — funcionó bien así el
   2026-08-14: Nicolás subió los 3 archivos pegándolos en GitHub y el
   resultado, verificado con `git diff`, fue byte-idéntico a lo entregado.**

Antes de un cambio con riesgo de romper el login o el acceso a datos
(middleware, callback de auth, policies, variables de entorno), además:
explicitar qué pasa con una sesión ya iniciada, qué pasa con un usuario a
mitad del flujo de signup, y cómo se revierte si algo sale mal (ver §24
para secretos).

**7. Distinguir siempre, igual que en §15 para Cartera:** chequeo
sintáctico ≠ compilación real de Next.js con los tipos del proyecto ≠
prueba en navegador. **Nota 2026-08-14: `npm install` + `tsc --noEmit` SÍ
funcionan en este sandbox — si el cambio toca firmas de función o varios
archivos, correr el type-check completo, no conformarse con parsear.**
Sigue sin haber Playwright ni el toolchain completo de build de Next.js
(`next build`) — decirlo explícitamente cuando aplique, no dar a entender
que se corrió el build real si no se corrió. **Pero si el usuario ya subió
el cambio y Vercel lo desplegó, SÍ se puede verificar en vivo con Claude en
Chrome (ver §15) — es la validación más fuerte disponible, mejor que
cualquier smoke test, y conviene hacerla apenas el usuario confirma que
subió los archivos.**

**8. Sub-pestañas por query param: cada Server Action pide su propio
destino explícito, nunca se infiere de otro parámetro compartido.**
Patrón establecido 2026-08-14 (`?tab=`/`?rtab=`/`?mtab=` + un Client
Component chico que hace `display:none` según `useSearchParams()`, sin
re-fetch al cambiar de sub-pestaña — ver §17 y componentes `Seccion.tsx`/
`SubTabRendimiento.tsx`/`SubTabMovimientos.tsx`). Bug real encontrado
antes de subir (no llegó a producción): el primer diseño de
`SubTabMovimientos` hacía que la sola presencia de `?error=` en la URL
seleccionara automáticamente la sub-pestaña "Precios manuales" — pero
`crearMovimiento`/`crearCaucion` (Server Actions del modal global
"+ Movimiento", `actions.ts`/`caucion-actions.ts`) **también** redirigen
con `?error=` a la misma ruta `/dashboard/movimientos`, sin relación
ninguna con precios manuales. Con esa inferencia, un error de esas dos
acciones habría mandado al usuario a la sub-pestaña equivocada. Arreglo:
`precio-actions.ts` pide `?mtab=precios` explícito en sus propios 3
`redirect()`, y la pantalla no infiere nada — solo lee `?mtab=` tal cual
vino, con "historial" como default. Además se mantiene un banner de error
genérico, visible sin importar la sub-pestaña activa, para que ningún
error quede invisible pase lo que pase. **Al agregar una sub-pestaña
nueva:** listar primero TODAS las Server Actions que puedan redirigir a
esa misma ruta (no solo las que a primera vista "pertenecen" a esa
sub-pestaña) antes de decidir si algún parámetro de la URL puede usarse
como señal implícita de a dónde aterrizar.

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
  que no cambie. Mismo criterio para la contraseña/URI de Postgres y para
  `SUPABASE_SERVICE_ROLE_KEY` si el usuario los comparte en el chat: se
  usan para esa conversación puntual y no se persisten en ningún doc.
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
- **Nota de infraestructura (2026-08-14):** el host directo de Postgres
  (`db.<proyecto>.supabase.co:5432`) resuelve solo por IPv6. Un sandbox de
  Claude sin salida IPv6 no puede conectarse ahí ni tampoco al connection
  pooler IPv4 (puerto 6543) si la política de red del entorno no permite
  ese destino. La API REST de Supabase (`https://<proyecto>.supabase.co/
  rest/v1/...`) sí resuelve por IPv4 — confirmado funcionando con la
  service_role key que Nicolás compartió en el chat para el diagnóstico de
  §6 regla 15: `GET /rest/v1/<tabla>?user_id=eq.<uuid>&select=...` con
  headers `apikey` y `Authorization: Bearer <key>`. Para diagnósticos de
  datos desde una sesión sin salida IPv6, esa es la vía. La key se usó solo
  para esa conversación puntual, no quedó guardada en ningún archivo de
  project knowledge ni en el repo — mismo criterio que cualquier otro
  secreto (ver el resto de esta sección). Nicolás la agregó también a las
  instrucciones del proyecto por su cuenta; eso es una decisión suya sobre
  su propio proyecto, no algo que Claude haya guardado.
- **Nota de infraestructura (2026-08-14, más tarde): el proxy de git de
  este sandbox distingue lectura de escritura por repo, independientemente
  del token usado.** `git clone`/`git fetch` de `nicofestu/cartera-app` con
  un PAT embebido en la URL (`https://<token>@github.com/nicofestu/
  cartera-app.git`) funcionan sin problema. `git push` al mismo remoto,
  con el mismo token, para el mismo repo (probado contra `main` y contra
  una rama nueva) es rechazado por el proxy: *"nicofestu/cartera-app is
  not in this session's authorized repository set"* — un bloqueo de sesión,
  no un problema de permisos del token. `api.github.com` está bloqueado
  por completo para este repo (lectura y escritura), mismo mensaje. No hay
  ninguna tool disponible en esta sesión para pedir acceso de escritura
  (`add_repo` u otra). **Consecuencia práctica: no prometer un commit o
  push real hasta haberlo probado.** Si el usuario autoriza un commit
  directo (§23.6), hay que intentarlo y, si el proxy lo bloquea, avisar
  explícitamente y entregar archivo completo + patch de git en su lugar —
  nunca reportar como "subido" algo que no se pudo subir. **Resultado
  2026-08-14: con archivo completo + ruta exacta, Nicolás pudo subir los 3
  archivos él mismo pegándolos en GitHub, y el resultado fue exacto (`git
  diff` contra el commit local no pusheado: idéntico salvo una línea en
  blanco final) — el flujo de fallback funciona bien en la práctica.**

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
   no una copia parcial. Ampliado el 2026-08-13 (noche, commit `b055564`):
   cron propio de precios de mercado para "todo el universo AR" — ya no
   depende de refrescar la página para tener cotizaciones al día.
4. **Migración de datos históricos del gist legado** — ✅ hecho
   (2026-08-11/12, ver commits `619166e`…`8a9846b`, con un fix de dedupe
   posterior en `ce19875`). Dos partes:
   - **`DATOS.movimientos` del gist** → tabla `movimientos` de
     cartera-app. Mapeo directo campo a campo.
   - **`DATOS.snapshots` del gist** → tabla `snapshots` de cartera-app,
     con la salvedad ya declarada de que el legado calculaba esos NAV
     históricos con ajustes que cartera-app no tenía porteados en ese
     momento (factor de ratio de CEDEAR, liquidación T+n).
5. **Rendimientos** — ✅ **cerrado 2026-08-14 (noche).** Núcleo financiero
   completo (retorno acumulado, Modified Dietz por tramo, TIR/XIRR,
   selector de período, benchmark contra S&P 500/Nasdaq 100), hecho entre
   el 2026-08-11 y el 2026-08-12. La discrepancia de Retorno Total/TIR
   "Todo" contra el legado (causa: aporte implícito por pool global en vez
   de por cuenta — ver §6 regla 15) se diagnosticó, arregló, entregó,
   Nicolás la subió y se CONFIRMÓ EN VIVO el mismo día: brecha de retorno
   32,00%/39,2% (7,2pp) → 33,40%/34,5% (1,1pp); TIR 129,19%/168,2% (39pp)
   → 135,44%/141,2% (5,8pp). Ver la entrada de "Última revisión" 2026-08-14
   noche, arriba del todo, para el detalle completo. Simplificación que
   sigue declarada en `rendimiento.ts`: sin liquidación T+n (candidata a
   explicar la brecha residual, sin confirmar). En `benchmark.ts`: sin
   `detectarRatiosNoDeclarados`.
6. **Importadores de bróker** — ✅ hecho (2026-08-13). Puente (PDF, hecho
   antes), Balanz e IEB+ (.xlsx, commit `eb0a0c2`) y Cocos (CSV múltiple,
   commit `67320fb`).

### Hito 7+ — paridad completa con Cartera

Se prioriza según lo que el usuario más use, no en el orden en que está
escrito acá. Actualizado 2026-08-14 (ver auditoría de esa fecha para el
detalle de cada verificación):

- Métricas de riesgo: Sortino, alfa de Jensen, volatilidad, Sharpe (§10)
  — ✅ hecho (2026-08-13, `#11`, commit `28755b4`). Necesitó portar además
  una serie de tasa libre de riesgo (`lib/cartera/tasas.ts`, nuevo).
- Reconstrucción de NAV histórico (`reconstruirHistorialSnapshots`, §11)
  y el gráfico de evolución de cartera en el tiempo — ✅ hecho
  (2026-08-13, PR #9, merge `476056a`). Puerto acotado: reutiliza
  derivarPosiciones/calcularCajaNativa/posicionesCaucion (ya aceptaban
  fecha de corte) contra precios públicos de `historial/{año}.json` +
  MEP histórico. SIN la lógica de REPARAR un snapshot `hist:true` ya
  guardado (ese bug del legado — caja excluida del NAV — nunca existió
  en cartera-app, `armarFilaSnapshot` siempre incluyó la caja). SIN
  factor de ratio de CEDEAR (mismo criterio que la valuación de hoy) y
  SIN `sp`/`ndx` fosilizado por snapshot. `lib/cartera/historial.ts`.
  Además se agregó un gráfico de % rendimiento time-weighted
  (`serieAcumulada()` en rendimiento.ts, encadena `serieDiaria()` igual
  que `retornoEntre` — con test cruzado entre las dos para no repetir el
  bug de la regla 14) porque el primer gráfico (NAV absoluto en pesos)
  no es comparable con "Rendimiento acumulado" de la app vieja — miden
  cosas distintas, no era un bug. Ampliado el 2026-08-13 (noche):
  reconstrucción de historial de FCI vía argentinadatos.com/CNV
  (`cb2c1eb`) y de ONs vía `datos/precios` del legado (`ff1ac77`), ambos
  ya SIN depender del repo legado en tiempo de ejecución para esos dos
  tipos de activo. **Auditoría 2026-08-14:** el gráfico de % existe pero
  vive en la pestaña Rendimientos; Inicio sigue mostrando NAV absoluto
  en esa posición — ver ítem "Header persistente y mini-gráfico de
  Inicio" más abajo.
- Vistas ARS / MEP / CCL intercambiables (§8) — ✅ hecho (2026-08-13,
  PR #7, merge `e9d84af`).
- Formulario de precios manuales en la UI — ✅ hecho (2026-08-13, PR #8,
  merge `e0d9de2`). La tabla `precios_manuales` y su lectura en
  `lib/cartera/nav.ts` ya existían; faltaba la pantalla.
- Saldos declarados por cuenta y liquidación T+n de la caja — ✅ hecho
  (2026-08-13, PR #6). Rediseñado a mitad de camino: la primera versión
  guardaba un delta FIJO en una tabla aparte (`saldos`), y en producción
  se vio en vivo que un delta migrado del historial viejo quedaba
  desactualizado e inflaba el NAV. Se reemplazó por un movimiento real
  (`op="ajuste"`, tabla `movimientos`) calculado una sola vez al
  guardar — sin delta que se pueda desactualizar, mismo espíritu que la
  advertencia de la regla 13 pero resuelto con un diseño distinto (un
  movimiento más, no un ajuste fijo aparte). Las tablas `saldos` y
  `saldos_historial` quedan en el esquema sin usarse (no se borraron).
  **Auditoría 2026-08-14:** el formulario funciona ("Declarar saldo",
  dentro de la pestaña Movimientos) pero no tiene ningún acceso directo
  desde otras pestañas — ver ítem "Acceso rápido a Movimientos y Saldos"
  más abajo.
- Principales contribuidores/detractores, tabla de retorno por activo —
  ✅ hecho (2026-08-13, PR #10, merge). Simplificación declarada: solo
  posiciones ABIERTAS hoy, no posiciones cerradas dentro de un período
  (falta portar `posicionesCerradasEnPeriodo`/`remarcarAMercado` del
  legado). **Actualización 2026-08-14 (noche):** `remarcarAMercado()` SÍ
  se portó, pero para un uso distinto (P&L realizado por período, ver
  ítem nuevo más abajo) — `posicionesCerradasEnPeriodo` (que alimentaría
  esta tabla con posiciones YA CERRADAS dentro del período, no solo las
  abiertas hoy) sigue sin portar. La simplificación declarada acá sigue
  vigente tal cual.
- Identidad visual (§17) y fondo NASA (§13) — ✅ hecho (2026-08-13, tanda
  de ~20 commits `c62d220`…`0168071`). Paleta, tipografía, tabs
  subrayados, cards, tablas, estados vacíos, transición fadeIn, botones
  pill, fondo NASA — verificado en vivo el 2026-08-14, ambas apps se ven
  casi idénticas. Ver §17 para lo que todavía difiere (header persistente,
  mini-gráfico de Inicio).
- Página de Ayuda + tooltips explicativos — ✅ hecho (2026-08-13,
  `e9ab754`), `/dashboard/ayuda` + componente `InfoTip`, sacando los
  párrafos explicativos que antes vivían sueltos en la pantalla de
  Cartera.
- Panel Macro (dólares, commodities, tasas) y resto de la pestaña Mercado
  (buscador y paneles en vivo de bonos, letras, ONs, acciones y CEDEARs
  más allá de lo que el usuario ya tiene en cartera) — **pendiente**. La
  propia app lo declara en pantalla ("Todavía no está portado desde
  Cartera legado") en vez de mostrar algo a medias — buena práctica,
  coincide con §1.5.
- Importadores de bróker además de Puente: Balanz, IEB+, Cocos — ✅ hecho,
  ver hito 6 más arriba (ya no es un ítem de hito 7+, se cerró como parte
  del núcleo).
- Diagnósticos en pantalla (brechas de datos, sobreventas, tramos
  descartados por `serieDiaria()`, etc.) — pendiente. El legado expone
  esto (`inestables`, avisos de cobertura); cartera-app todavía no tiene
  una pantalla equivalente.
- **Discrepancia de Retorno Total/TIR "Todo" entre apps — ✅ CERRADO
  2026-08-14 (noche).** Ver hito 5 más arriba: causa confirmada,
  implementada, subida por Nicolás y confirmada en vivo. Brecha residual
  chica (~1-6pp) sin investigar más — candidata: liquidación T+n.
- **Acceso rápido a Movimientos y Saldos desde cualquier pestaña — ✅
  RESUELTO.** `components/AccesoRapido.tsx`: botones globales
  "+ Movimiento" / "Saldos" en el header (vía `TabBar.tsx`), visibles con
  un clic desde cualquier pestaña, abren un modal (portal a
  `document.body` — hay una nota en el propio archivo sobre un bug real
  de `backdrop-filter` creando un containing block que recortaba el
  modal, ya solucionado). Reusa los mismos formularios y Server Actions
  de siempre, sin duplicar lógica. **Se hizo en una sesión anterior no
  documentada acá** — este documento seguía diciendo "sigue pendiente"
  mientras el código ya lo tenía resuelto (auditoría 2026-08-14 tarde-
  noche, al retomar el Plan de mejoras UX/UI: se confirmó que el archivo
  ya existía y funcionaba antes de tocar nada). **Decisión explícita de
  Nicolás, 2026-08-14 tarde-noche, confirmada dos veces en la misma
  sesión:** estos botones quedan DONDE ESTÁN — no se mueven a ninguna
  sub-pestaña de Movimientos ni se duplican en ningún otro lado (ver PR4
  del Plan de mejoras UX/UI, entrada de "Última revisión" arriba del
  todo).
- **Header persistente estilo legado (título/timestamp/"...") — decisión
  tomada: NO se construye.** 2026-08-14 tarde-noche: Nicolás confirmó
  explícitamente que el diseño actual (accesos rápidos en `TabBar.tsx`,
  sin título/timestamp/menú "..." fijos como el legado) es la decisión
  final, no un pendiente. No hay trabajo futuro esperado acá salvo que
  Nicolás lo reabra explícitamente.
- **Mini-gráfico de Inicio en % (en vez de NAV absoluto) — sigue
  pendiente, sin tocar.** El % time-weighted ya existe y está probado en
  la pestaña Rendimientos (`serieAcumulada()`); en Inicio, el mini-
  gráfico de "Evolución de cartera" sigue mostrando NAV absoluto en
  pesos. Técnicamente es solo decidir cuál de los dos gráficos ya
  existentes se muestra ahí — no se abordó en la sesión de mejoras
  UX/UI del 2026-08-14 (el Plan de Claude Design no lo incluía), NI en
  el rediseño de Inicio de esa misma noche (pedido puntual: achicar NAV
  + Liquidez por pool + Posición por cuenta, no tocó el gráfico).
- **P&L realizado por período — ✅ hecho (2026-08-14, noche).** Antes
  solo existía "Todo" (histórico completo, vía `derivarPosiciones()`);
  ahora funciona para Hoy/Semana/Mes/YTD/1A también, con remarcado a
  mercado (`lib/cartera/realizado.ts`, puerto de
  `remarcarAMercado()`/`realizadoEnPeriodo()` del legado). Mismas
  simplificaciones declaradas que el legado: tipo `fci` y `manual` no se
  remarcan. Ver entrada de "Última revisión" arriba del todo para el
  detalle y la validación.
- **Capital aportado/retirado en Inicio (luego movido a Rendimientos) —
  ✅ hecho (2026-08-14, noche).** `ultimoHito.apor`/`.ret`
  (`construirHitosCaja()`, ya existía) expuesto como dos cards nuevas,
  cross-convertidas a la vista elegida.
- **Bug de CCL en `cajaARS` y en cauciones pooleadas en CCL — ✅
  ARREGLADO 2026-08-14 (noche).** `nav.ts` usaba el dólar MEP para el
  pool de caja CCL y para cauciones en pool CCL, en vez del CCL real —
  ver §8 para el detalle completo y la corrección de la premisa "no
  existe CCL histórico" que motivó el bug original.
  `historial.ts` (reconstrucción de cierres pasados) queda con el mismo
  criterio corregido — ver §26bis.
- **Independencia de datos históricos (repo legado + argentinadatos.com
  en vivo) — ✅ hecho (2026-08-14, noche), a pedido de Nicolás.** Ver
  §26bis para el detalle completo: backfill de precios (1.129 fechas) y
  dólares (~5.000 fechas) a tablas propias, `historial.ts` reescrito
  para leer local primero, cron de precios de mercado diagnosticado y
  confirmado funcionando.
- **Snapshots históricos recalculados con el motor propio de
  cartera-app (en vez de los migrados del legado) — ✅ hecho
  (2026-08-14, noche).** Los 104 snapshots que había estaban migrados en
  bloque desde el gist del legado (`importar-legado`, hito 4), calculados
  con el motor VIEJO de caja (un solo pool, sin por-cuenta ni tope de
  compra ni T+n) — no eran cálculo propio de cartera-app. Backup
  entregado (104 filas, JSON), los 104 borrados, reconstruidos con
  "Reconstruir historial hacia atrás" (motor actual, con el fix de CCL y
  las tablas propias de §26bis). Resultado: **89 filas** (antes 104) —
  15 fechas (2026-05-06 a 05-20, más 4 sueltas fin de julio/inicio de
  agosto) quedaron sin snapshot, declaradas incompletas en vez de
  fabricadas. Investigado: NO es un problema de cobertura de PLTR/ECOG
  (ambas tienen cobertura completa en `historial/2026.json` para esas
  fechas, confirmado); coincide con la fecha en que se cargó una posición
  de FCI (2026-05-06) — el histórico de FCI queda deliberadamente FUERA
  del backfill de §26bis (sigue en vivo, per-fondo, vía
  `fetchHistoricoFciFondo`), así que lo más probable es que ese fondo
  puntual tenga un hueco de cobertura en argentinadatos.com para esa
  ventana. No es una regresión de este cambio: es la reconstrucción REAL
  validando cobertura por primera vez — los 104 viejos nunca habían
  pasado por esa validación, se habían migrado tal cual del legado sin
  chequeo. Coincide con el criterio de §1.5 ("un dato faltante se
  declara") — se prefieren 89 cierres reales a 104 con algunos
  fabricados.

### Qué significa "terminado"

cartera-app no se considera terminado mientras falte algo de esta lista,
salvo que el usuario decida explícitamente excluirlo (y en ese caso se
anota acá el motivo, no se borra en silencio — mismo criterio que "un
dato faltante se declara" de §1). Cada hito nuevo que se complete se
marca ✅ con fecha y referencia al PR, igual que el hito 1.

---

## 26bis. Independencia de datos históricos (2026-08-14)

A pedido de Nicolás ("que no dependa de nada externo"): cartera-app dejó
de recalcular todo, cada vez, contra el repo legado y argentinadatos.com
en vivo. Dos tablas nuevas en Supabase, mismo criterio de RLS que
`precios_mercado_diarios` (dato público de mercado, sin `user_id`,
lectura abierta, escritura solo con service role):

- **`public.precios_mercado_diarios`** (ya existía desde el cron de
  precios de mercado, hito 7+): backfill de 1.129 fechas
  (2022-01-03 a 2026-08-14), migradas desde `historial/{2022..2026}.json`
  + `datos/precios/on-{c,d}.json` del repo legado (mismo formato
  `{tipo:{ticker:precio}}` que ya usaba la tabla, ningún esquema nuevo).
- **`public.dolares_diarios`** (tabla nueva, ver `supabase/schema.sql`):
  backfill de MEP (2.844 fechas, 2018-10-29 a hoy) y CCL (4.970 fechas,
  2013-01-02 a hoy), desde argentinadatos.com (casas `bolsa` y
  `contadoconliqui`).

**`lib/cartera/historial.ts` reescrito** — `fetchHistorialPrecios`,
`fetchMepHistorico`, `fetchCclHistorico` consultan la tabla propia
PRIMERO (con paginación, `paginarTodo()`, porque de a 1000 filas es el
tope de PostgREST); si no hay nada para el rango pedido (o la consulta
falla), caen al fetch externo de siempre — la dependencia externa queda
como red de seguridad, no como camino principal. `fetchPreciosBolsarOn()`
(Bolsar, on-c/on-d.json) quedó como parte INTERNA del fallback de
`fetchHistorialPrecios` en vez de un paso separado que cada caller tenía
que acordarse de fusionar — `reconstruirHistorialSnapshots()` y
`fetchPreciosParaRemarcado()` se simplificaron en consecuencia (ya no
llaman ni fusionan ON por separado).

**Cron de precios de mercado, diagnosticado y confirmado funcionando**
(`app/api/cron/precios-mercado/route.ts`): existía desde hace ~2 semanas
pero nunca había escrito una fila (`precios_mercado_diarios` en cero).
Diagnóstico en vivo con Nicolás mirando el dashboard de Vercel — plan
Hobby retiene logs de ejecución solo 1 HORA, así que revisar hacia atrás
no sirve de nada; hubo que ubicar la pantalla nativa de Cron Jobs
(`Deployments` → deployment de producción → sección "Cron Jobs" — la de
"Integrations → Cron" del marketplace es un integration de terceros no
relacionado) y disparar una corrida para ver el resultado en caliente. La
corrida devolvió 200 con datos reales (bono 185, letra 25, on 627, acción
95, cedear 941, FCI 3.680 fondos), y la corrida programada de esa misma
tarde (21:35 UTC, con el margen de imprecisión de hasta una hora que
tiene el plan Hobby) también escribió sola — confirmado que el cron ya
está autónomo. **No se encontró la causa raíz de por qué no había corrido
nunca antes** — no hay evidencia de ningún error puntual; la hipótesis
más probable es que algún deploy anterior a esta sesión no haya
registrado bien el cron nuevo en el scheduler de Vercel, y alguno de los
redeploys de esta sesión lo destrabó de rebote. Se declara la incerteza
en vez de inventar una causa. De paso, el cron ahora TAMBIÉN escribe
MEP/CCL del día en `dolares_diarios` (antes solo precios de activos) —
`fetchDolares()` de `lib/cartera/precios.ts`, mismo criterio que usa el
resto de la app en vivo.

**Alcance deliberadamente NO incluido en este backfill**: FCI histórico
por fondo (`fetchHistoricoFciFondo`, argentinadatos.com) sigue en vivo,
sin backfill — es per-fondo, no una serie única, y "todo el universo de
FCI históricos" implicaría enumerar y traer el histórico de cientos de
fondos; no era lo que pedía Nicolás ("la data que tomamos del OTRO REPO"
— el legado nunca tuvo FCI, así que no aplica acá). Si en algún momento
hace falta, es un proyecto aparte con su propio alcance a definir.

---
