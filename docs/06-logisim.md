# Paso 6 — Implementación de Logisim Evolution (prototipo)

**Fecha:** 18/11/2026  
**Archivo:** [`cpu16_harvard_prototipo.circ`](../logisim/cpu16_harvard_prototipo.circ)  
**Objetivo:** implementación del diseño Harvard monociclo de 16 bits acordado en pasos 1–5.  
**Estado:** conectividad estructural corregida y revisada (19/11/2026); **no ejecutado todavía dentro de Logisim Evolution**. No se afirma funcionamiento eléctrico ni temporal verificado.

## Corrección de conectividad — 19/11/2026

**Incidencia detectada por el usuario:** al abrir el archivo original, los subcircuitos aparecían aislados. La auditoría descubrió que el generador había creado elementos y túneles sin cables explícitos (solamente dos segmentos de cable en todo el archivo) y que el *custom appearance* de los subcircuitos tenía los puertos desalineados respecto de la ubicación calculada de sus instancias.

**Correcciones realizadas sobre el archivo versionado:**
- Se agregaron **685 segmentos físicos de cable** entre puertos de componentes y túneles, además de algunos buses visibles entre PC, ROM, IR y CONTROL.
- Se alinearon las coordenadas del icono de cada subcircuito (puertos y ancla) para que correspondan a los terminales en CPU16.
- Se evitó conectar accidentalmente entradas próximas (por ejemplo, WA/WE del decodificador y datos/selectores de MUX).
- Se conectó mediante un cable explícito el cero al clear de las 16 palabras de RAM.
- Se corrigió `tools/build_logisim.py` para que el proyecto pueda regenerarse con esas conexiones y sin rutas absolutas.

Los **túneles con la misma etiqueta y el mismo ancho** forman una conexión eléctrica dentro de un mismo circuito. Por eso algunos bloques conservan una presentación modular en lugar de una única línea larga de extremo a extremo, aunque ahora las patillas desembocan en cables y túneles. **El chequeo es estructural**: aún se necesita abrir y simular el .circ en Logisim Evolution para certificar el comportamiento en ejecución.

**Recomendación:** cerrar sin guardar la versión vieja y volver a descargar el archivo actualizado desde `logisim/cpu16_harvard_prototipo.circ`. Abrir el circuito principal `CPU16` y luego los subcircuitos.

## 1. Estructura del proyecto

El `.circ` contiene **7 circuitos**:

| Circuito | Responsabilidad |
| --- | --- |
| `CPU16` | Datapath principal: PC, ROM, muxes, control, banco, ALU, memoria y flags |
| `CONTROL` | ROM de decodificación combinacional de 16 palabras + validación de campos y saltos |
| `ALU16` | ALU de 16 bits: ADD, SUB, AND, OR; Z, N, C (préstamo), V |
| `REGS12` | 12 registros R4–R15 de 16 bits, 2 lecturas combinacionales y 1 escritura síncrona |
| `RAM16_ASYNC` | RAM de 16 palabras de 16 bits construida con registros y multiplexores |
| `SEXT8` | Extensión de signo de `imm8` a 16 bits |
| `SEXT12` | Extensión de signo de `offset12` a 16 bits |

### Notas de implementación

- **Logisim Evolution 5.0.0:** el prototipo utiliza las bibliotecas y atributos de su formato `.circ` (puede requerir ajustes en otras versiones).
- ROM de instrucciones: una palabra de 16 bits por dirección, **bus PC de 16 bits**. Está cargada con las 13 instrucciones del programa de ejemplo (PC 0..12).
- RAM: **16 palabras de 16 bits** con direccionamiento lógico de 16 bits; direcciones `0..15` válidas. Para direcciones `>=16`, la RAM retorna 0 y no escribe. Esta elección concreta el parámetro `M` que la consigna deja libre. **No hay alias de direcciones**.
- **Por qué la RAM se construye con registros:** la RAM estándar de Logisim Evolution 5.0.0 puede tener lectura con salida registrada; esa modalidad agregaría una latencia incompatible con la carga monociclo. Aquí se utilizan registros + MUX de lectura combinacional, y la escritura sucede en el flanco ascendente.
- El banco de registros se reinicia a cero con `RESET`. El reset no borra la RAM: permite precargar el array y reiniciar el procesador para probarlo.
- Se agregó una interfaz de **depuración** que escribe la RAM con `RUN=0` sin mover el PC. No forma parte del ISA; sólo se usa para preparar datos en la simulación.
- `OR` inclusivo y política de flags siguen provisionales hasta confirmar con el docente. La ALU incluida es una nueva realización y debe adaptarse a la **ALU desarrollada en clases** si ese circuito se entrega.

## 2. Interfaces visibles de CPU16

| Puerto | Dirección | Bits | Uso |
| --- | --- | ---: | --- |
| `CLK` | Entrada | 1 | Generar manualmente flancos `0→1→0` |
| `RESET` | Entrada | 1 | Nivel 1 reinicia PC, flags y registros; RAM conserva valores |
| `RUN` | Entrada | 1 | `0`: PC, banco y flags en pausa; `1`: ejecutar |
| `DBG_ADDR` | Entrada | 16 | Dirección de RAM durante la pausa |
| `DBG_DIN` | Entrada | 16 | Dato a escribir durante la pausa |
| `DBG_WRITE` | Entrada | 1 | Habilita escritura de depuración durante la pausa |
| `PC` | Salida | 16 | PC actual (dirección por palabra) |
| `IR` | Salida | 16 | Instrucción entregada por ROM |
| `R4` | Salida | 16 | Índice de búsqueda |
| `FLAGS` | Salida | 4 | bits `[3:0] = V C N Z` |
| `RAM0` | Salida | 16 | Inspección del dato RAM[0] |
| `VALID` | Salida | 1 | `ValidInstr` de la unidad de control |

### Condición de flanco

Con `RUN=1`, el PC, el banco y el registro de flags capturan datos en el mismo flanco ascendente; la RAM sólo escribe con `STORE` válido. Con `RUN=0`, el PC y los registros/flags se mantienen, pero `DBG_WRITE=1` puede escribir la RAM en el mismo flanco. El reset inhibe las escrituras de RAM.

## 3. Programa precargado en ROM

Formato de línea: dirección por palabra, ensamblador y hexadecimal.

| PC | ASM | HEX |
| ---: | --- | --- |
| 0 | `MOV #0, R4` | `8400` |
| 1 | `MOV #100, R5` | `8564` |
| 2 | `MOV #0, R7` | `8700` |
| 3 | `MOV #10, R8` | `880A` |
| 4 | `MOV @R7, R6` | `6760` |
| 5 | `CMP R5, R6` | `4560` |
| 6 | `JZ encontrado` | `A006` |
| 7 | `ADD #1, R4` | `9401` |
| 8 | `ADD #1, R7` | `9701` |
| 9 | `CMP R8, R4` | `4840` |
| 10 | `JNZ buscar` | `BFFA` |
| 11 | `fin: JMP fin` | `C000` |
| 12 | `encontrado: JMP encontrado` | `C000` |

El `JZ` en PC=6 tiene offset `12-6=6`. El `JNZ` en PC=10 tiene offset `4-10=-6`. Los dos `JMP 0` permanecen sobre la misma palabra.

También se adjunta [`programa_busqueda.hex`](../rom/programa_busqueda.hex) para importar el contenido en la ROM desde Logisim.

## 4. Procedimiento de prueba manual

1. Abrir el archivo `.circ` en **Logisim Evolution 5.0.0** y seleccionar el circuito `CPU16`.
2. Fijar `CLK=0`, `RUN=0`, `DBG_WRITE=0`; activar `RESET=1` y luego volver a `RESET=0` (debe verse PC=0, R4=0, FLAGS=0).
3. Con `RUN=0`, cargar diez elementos mediante las entradas de depuración: para cada elemento, colocar la dirección en `DBG_ADDR`, el valor en `DBG_DIN`, activar `DBG_WRITE=1`, dar un flanco `CLK: 0→1→0` y desactivar `DBG_WRITE=0`.
4. Utilizar este array de ejemplo, con `100` en la posición 5:

   | Dirección | Valor decimal |
   | ---: | ---: |
   | 0 | 12 |
   | 1 | 23 |
   | 2 | 34 |
   | 3 | 45 |
   | 4 | 56 |
   | 5 | **100** |
   | 6 | 78 |
   | 7 | 89 |
   | 8 | 90 |
   | 9 | 11 |

5. Con `DBG_WRITE=0`, pulsar `RESET=1→0` para iniciar el programa desde PC=0 sin borrar la RAM.
6. Poner `RUN=1` y generar flancos ascendentes en `CLK` uno a uno, mirando `PC`, `IR`, `R4` y `FLAGS`.
7. **Resultado esperado** en el modelo funcional: `PC=12`, `R4=5`, y sucesivos flancos no cambian el PC (bucle `JMP 0`).
8. Para el caso no encontrado, precargar diez valores distintos de 100, reiniciar y ejecutar. **Resultado esperado** del modelo: `PC=11`, `R4=10`, bucle infinito.

Estas son **expectativas calculadas por el simulador de referencia Python**, no resultados observados aún en Logisim. Si aparece un error de carga, un bus naranja/rojo o un resultado inesperado, revisar primero la compatibilidad de versión, las señales de control, los puertos de los subcircuitos y los anchos de cables.

## 5. Verificación efectuada y pendiente

- **Realizada:** comprobación de XML bien formado, existencia de los 7 circuitos, anchos coherentes de túneles y puntos de conexión de componentes usados, contenido de ROM conforme al ensamblador; pruebas Python previas del modelo de ISA, ALU y datapath.
- **Pendiente:** apertura y ejecución en Logisim Evolution 5.0.0, validación de la RAM de registros, pruebas de todos los caminos de datos contra vectores, y una demostración de la búsqueda lineal en el archivo `.circ`.
- **Pendiente académica:** incorporar la ALU exacta utilizada en las prácticas de clase, si la cátedra requiere conservar su estructura.

## 6. Cómo regenerar el circuito

El generador reproducible se encuentra en [`tools/build_logisim.py`](../tools/build_logisim.py) y también en el paquete descargable. Requiere Python 3.10+ y bibliotecas estándar. Regenera el XML y muestra los códigos hexadecimales de ambas ROM. El archivo `.circ` es editable en Logisim Evolution.

## 7. Referencias

- Consigna del integrador 2025, apuntes de clases 1–6 y resolución CD 336/25 aportados a este proyecto.
- Logisim Evolution, [versión 5.0.0](https://github.com/logisim-evolution/logisim-evolution/releases/tag/v5.0.0).
- Referencias de formato de componentes y prueba: documentación de Logisim Evolution y ejemplos publicados en logisim.dev (ROM, registros, multiplexores y RAM).