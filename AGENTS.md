# Contexto e instrucciones del proyecto Cartera

## 1. Identidad del proyecto

- **Repositorio:** `nicofestu/Cartera`
- **Rama principal:** `main`
- **Archivo principal:** `index.html`
- **Tipo de aplicación:** aplicación web monolítica en HTML, CSS y JavaScript.
- **Objetivo:** seguimiento integral de portfolios de inversión, movimientos, posiciones, liquidez, rendimientos, riesgo, benchmarks y cotizaciones.
- **Usuario principal actual:** Nicolás Festugato.
- **Idioma de la interfaz y de las respuestas:** español.

El archivo `index.html` es la aplicación completa. Contiene estructura HTML, estilos, lógica, persistencia, importadores, sincronización, cálculos financieros y renderizado.

---

## 2. Fuente de verdad

Antes de modificar código:

1. Leer siempre la última versión de `index.html` de la rama `main`.
2. Verificar que no exista una versión más reciente adjuntada por el usuario en la conversación.
3. Si el usuario adjunta un archivo más reciente, esa copia pasa a ser la fuente de verdad para esa modificación.
4. Nunca trabajar a partir de una copia local antigua sin verificarla contra GitHub.
5. Obtener el SHA actual del archivo antes de actualizarlo en GitHub.

No asumir que una versión vista en una conversación anterior sigue vigente.

---

## 3. Acceso a GitHub

Usar el conector de GitHub para:

- Leer archivos del repositorio.
- Consultar el SHA actual.
- Crear archivos nuevos.
- Reemplazar archivos existentes.
- Revisar ramas, commits, pull requests, issues y acciones cuando corresponda.

Repositorio objetivo:

```text
nicofestu/Cartera
```

Archivo principal:

```text
index.html
```

Al modificar directamente el repositorio:

1. Leer `index.html`.
2. Conservar el SHA devuelto por GitHub.
3. Aplicar el cambio sobre el contenido completo.
4. Validar el resultado.
5. Actualizar el archivo usando el SHA leído.
6. Evitar escrituras paralelas sobre el mismo archivo.

No pedir nuevamente acceso a GitHub salvo que el conector devuelva un error real de permisos o conexión.

---

## 4. Forma obligatoria de entrega

El usuario prefiere recibir siempre el archivo completo.

Para cualquier modificación de código:

- Entregar un `index.html` completo y listo para reemplazar.
- Conservar exactamente el nombre `index.html`.
- No entregar solamente fragmentos, diffs o instrucciones manuales.
- Un parche puede acompañar la entrega, pero nunca reemplazar al archivo completo.
- Incluir un resumen breve de los cambios.
- Informar qué validaciones se realizaron.
- Aclarar cualquier limitación real.

Cuando el usuario diga “subilo”, se puede actualizar GitHub.  
Cuando diga “dámelo para subir”, entregar el archivo descargable sin modificar el repositorio.

---

## 5. Principios de implementación

### 5.1 Cambios mínimos y dirigidos

- Modificar solo lo solicitado.
- No rediseñar otras pantallas sin pedido explícito.
- No refactorizar áreas no relacionadas.
- No cambiar nombres, claves de almacenamiento o formatos de datos sin necesidad.
- Mantener compatibilidad hacia atrás.

### 5.2 Preservación de datos

La aplicación usa datos locales y sincronizados que pueden provenir de versiones antiguas.

Toda función nueva debe tolerar:

- Campos opcionales ausentes.
- Movimientos creados por versiones anteriores.
- Datos importados de brokers.
- Datos sincronizados desde el gist.
- Formatos antiguos de `localStorage`.
- Campos con valores por defecto implícitos.

Nunca exigir al usuario borrar movimientos, reiniciar la cartera o reimportar todo para que una corrección funcione, salvo que sea estrictamente inevitable.

### 5.3 Compatibilidad de interfaz

- Preservar la estructura y estética existentes.
- Mantener la aplicación responsive.
- No duplicar listeners.
- No duplicar definiciones de funciones.
- No introducir dependencias nuevas sin justificación.
- Conservar la degradación elegante cuando una API externa falla.

---

## 6. Reglas financieras fundamentales

### 6.1 Flujos externos e internos

Distinguir siempre entre:

**Flujos externos de capital**
- Depósito real de dinero del usuario.
- Retiro real de dinero del usuario.

**Transformaciones internas**
- Compra de activos.
- Venta de activos.
- Reinversión.
- Movimiento de caja a una caución.
- Retorno del capital de una caución.
- Rotación entre instrumentos.
- Cambio de custodia o pool cuando no entra ni sale capital del patrimonio.

Solo los flujos externos deben modificar el capital aportado o retirado utilizado en Modified Dietz, TIR y demás métricas.

### 6.2 Cauciones

Una caución se representa mediante movimientos vinculados por `grupoCaucion`.

Puede contener:

- `capital_ini`
- `capital_venc`
- `interes`

Reglas:

- El capital inicial y el capital al vencimiento mueven la caja.
- Esos movimientos no son aportes ni retiros externos.
- Mientras la caución está vigente, el capital debe permanecer representado como posición sintética.
- El interés sí es rendimiento.
- Los movimientos históricos pueden no contener `caucionLeg`.
- La detección debe ser defensiva y usar también `grupoCaucion`, `caucionRol`, `caucionVenc`, tipo de operación y exclusión explícita del interés.

No depender exclusivamente de:

```js
m.caucionLeg === "capital_ini" || m.caucionLeg === "capital_venc"
```

porque movimientos antiguos o sincronizados pueden no tener ese campo.

### 6.3 Caja y NAV

Mantener como invariante:

```text
NAV = valor de posiciones + caja
```

La misma definición de caja debe usarse en:

- Inicio.
- Rendimientos.
- Snapshots diarios.
- Reconstrucción histórica.
- Normalización.
- Liquidez por cuenta.
- Métricas de riesgo.

No sumar la caja dos veces.

### 6.4 Monedas

La aplicación distingue:

- ARS.
- USD MEP.
- USD CCL.

También distingue pools nativos de efectivo:

- Pesos.
- Dólar local o MEP.
- Dólar exterior o CCL.

No tratar MEP y CCL como simples etiquetas visuales. Son custodias y tipos de cambio distintos.

Cuando no exista una serie histórica CCL confiable, mantener explícitamente la aproximación histórica existente y no inventar datos.

### 6.5 Rendimientos

- Modified Dietz debe excluir transformaciones internas.
- La TIR debe respetar la fecha exacta de cada flujo.
- El retorno time-weighted no debe confundirse con aportes o retiros.
- Los benchmarks deben usar una fuente coherente.
- No mostrar métricas si la cobertura de datos no permite calcularlas de forma honesta.
- Mantener las advertencias de cobertura y diagnóstico.

---

## 7. Integraciones y datos externos

Fuentes usadas actualmente:

- Data912 para instrumentos de BYMA.
- DolarAPI para tipos de cambio.
- ArgentinaDatos para FCI y series públicas.
- Archivos históricos del propio repositorio.
- GitHub Gist secreto para sincronización de movimientos.

Reglas:

- Tolerar fallas parciales de APIs.
- Un ticker inválido no debe romper toda la aplicación.
- No exponer tokens, IDs privados de gist ni datos personales.
- No incluir secretos directamente en el repositorio.
- La sincronización debe mantener compatibilidad entre dispositivos y versiones.

---

## 8. Validaciones obligatorias

Antes de entregar un `index.html` modificado:

### 8.1 Sintaxis

Extraer y validar todos los bloques `<script>` relevantes.

Usar, cuando corresponda:

```bash
node --check archivo.js
```

Si el código está embebido en HTML, extraer el bloque principal temporalmente y validarlo con Node.js.

### 8.2 Regresión

Crear o ejecutar una prueba mínima que reproduzca el problema corregido.

Para cauciones, verificar al menos:

1. Movimiento nuevo con `caucionLeg`.
2. Movimiento antiguo sin `caucionLeg`.
3. Caución colocadora.
4. Caución tomadora.
5. Capital inicial.
6. Capital al vencimiento.
7. Interés.
8. Que el capital no figure como aporte o retiro externo.
9. Que el retorno refleje únicamente el interés.

Ejemplo conceptual:

```text
Capital: ARS 1.000.000
TNA: 30%
Plazo: 3 días
Interés aproximado: ARS 2.465,75
Retorno esperado: aproximadamente +0,2466%
```

Nunca aceptar como correcto un resultado cercano a -100% provocado por el retorno del capital.

### 8.3 Integridad

Comprobar:

- Que el HTML completo siga abriendo.
- Que no existan funciones duplicadas.
- Que no existan listeners duplicados.
- Que se mantengan las claves de `localStorage`.
- Que no se haya truncado el archivo.
- Que el icono base64 y demás recursos embebidos permanezcan intactos.
- Que la modificación no haya eliminado accidentalmente secciones posteriores del archivo.

---

## 9. Flujo recomendado de trabajo

1. Leer la solicitud.
2. Leer la última versión completa del archivo.
3. Localizar la lógica involucrada.
4. Identificar la causa raíz.
5. Implementar el cambio mínimo.
6. Crear una prueba de regresión.
7. Validar sintaxis.
8. Comparar tamaño y estructura con el original.
9. Entregar el archivo completo.
10. Resumir brevemente:
   - causa;
   - cambio;
   - validación;
   - limitaciones.

---

## 10. Reglas de comunicación

- Responder en español.
- Ser directo y técnico, pero entendible.
- No afirmar que una corrección está validada si no se ejecutó una prueba.
- No decir que se accedió a GitHub si no se realizó una lectura real.
- No inventar archivos descargables.
- Verificar que todo enlace entregado exista realmente.
- No pedir información que ya está disponible en la conversación o el repositorio.
- Si una tarea compleja no puede completarse del todo, entregar el avance real y explicar exactamente qué falta.

---

## 11. Alcance actual del producto

La aplicación incluye, entre otras funciones:

- Registro y edición de movimientos.
- Compras, ventas, depósitos, retiros, rentas y gastos.
- Cauciones colocadoras y tomadoras.
- Importación desde distintos brokers.
- Posiciones por costo promedio ponderado.
- Caja y liquidez por cuenta.
- Saldos declarados.
- Valuación en ARS, MEP y CCL.
- Rendimientos por período.
- Time-weighted return.
- Modified Dietz.
- TIR efectiva anual.
- Sharpe, Sortino, volatilidad, drawdown y beta.
- Benchmarks S&P 500 y Nasdaq 100.
- Historial y reconstrucción de snapshots.
- Sincronización mediante GitHub Gist.
- Exportación e importación de respaldo.
- Mercado y cotizaciones.

Cualquier modificación debe considerar que `index.html` es un sistema integrado: un cambio en caja, movimientos o monedas puede impactar simultáneamente Inicio, Rendimientos, snapshots, riesgo y sincronización.

---

## 12. Preferencia permanente del usuario

La modalidad de trabajo preferida es:

```text
Archivo completo, listo para reemplazar, con cambios mínimos y validados.
```

No volver a entregar únicamente instrucciones de “buscar y reemplazar” cuando sea posible generar el archivo completo.
