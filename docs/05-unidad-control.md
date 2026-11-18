# Paso 5 — Unidad de control combinacional

**Proyecto:** Integrador Arquitectura de Computadoras 2026  
**Estado:** propuesta base según consigna 2025; verificada a nivel de decodificador de referencia, pendiente implementación en Logisim Evolution y confirmación del ISA 2026.  
**Dependencias:** [ISA](01-isa.md), [formatos de instrucción](02-formatos-instrucciones.md), [datapath](03-datapath.md) y [ALU/flags](04-alu-flags.md).

## 1. Objetivo, entradas y principio monociclo

La unidad de control **no almacena estado ni tiene FSM**: decodifica combinacionalmente `IR[15:0]` y el flag `Z_reg` almacenado. Determina los selectores del datapath, las habilitaciones de escritura y si se debe tomar un salto. La ROM entrega `IR` combinacionalmente; el PC, banco de registros, RAM y registro de flags se actualizan en el flanco ascendente según las habilitaciones.

**Entradas**: `IR[15:0]` (16 bits) y `Z_reg` (1 bit). El reset es una señal externa del circuito principal que tiene prioridad sobre el PC y registro de flags y debe inhibir escrituras durante su activación.

**Salidas**:

| Nombre | Bits | Función |
| --- | ---: | --- |
| `ValidInstr` | 1 | Código y campos válidos; 0 suprime efectos laterales |
| `DestSel` | 1 | 0: `Rd = IR[7:4]` (R); 1: `Rd = IR[11:8]` (I) |
| `ALUSrc` | 1 | 0: `ReadB`; 1: `sext(IR[7:0])` |
| `ALUOp` | 2 | `00` ADD, `01` SUB, `10` AND, `11` OR |
| `WBSel` | 2 | `00` ALU, `01` ReadB, `10` RAM, `11` inmediato extendido |
| `RegWrite` | 1 | Habilita escritura de `Rd` |
| `MemRead` | 1 | Identifica LOAD; conexión opcional a un read-enable de RAM |
| `MemWrite` | 1 | Habilita escritura sincrónica en RAM |
| `FlagWrite` | 1 | Habilita escritura del registro Z/N/C/V |
| `BranchKind` | 2 | `00` ninguno, `01` JZ, `10` JNZ, `11` JMP |
| `BranchTaken` | 1 | 1: próximo PC = `PC + sext(offset12)`; 0: `PC + 1` |

`MemRead` **no reemplaza** una lectura combinacional de RAM: para una carga monociclo, la palabra debe estar disponible antes del flanco de reloj. Si la RAM no admite una lectura combinacional, el datapath debe ajustarse.

## 2. Tabla de verdad por instrucción

Se especifican **todos los selectores con un valor definido**, incluso cuando el resultado no se utiliza, para evitar salidas flotantes e incógnitas en Logisim. `V` indica que el opcode y los campos exigidos son válidos. Los selectores y escrituras de instrucciones inválidas son cero.

| Op | Instrucción | DestSel | ALUSrc | ALUOp | WBSel | RegWrite | MemRead | MemWrite | FlagWrite | BranchKind |
| --- | --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | ADD R | 0 | 0 | 00 | 00 | 1 | 0 | 0 | 1 | 00 |
| 1 | SUB R | 0 | 0 | 01 | 00 | 1 | 0 | 0 | 1 | 00 |
| 2 | AND R | 0 | 0 | 10 | 00 | 1 | 0 | 0 | 1 | 00 |
| 3 | OR R | 0 | 0 | 11 | 00 | 1 | 0 | 0 | 1 | 00 |
| 4 | CMP R | 0 | 0 | 01 | 00 | 0 | 0 | 0 | 1 | 00 |
| 5 | MOV R | 0 | 0 | 00 | 01 | 1 | 0 | 0 | 0 | 00 |
| 6 | LOAD | 0 | 0 | 00 | 10 | 1 | 1 | 0 | 0 | 00 |
| 7 | STORE | 0 | 0 | 00 | 00 | 0 | 0 | 1 | 0 | 00 |
| 8 | MOV I | 1 | 0 | 00 | 11 | 1 | 0 | 0 | 0 | 00 |
| 9 | ADD I | 1 | 1 | 00 | 00 | 1 | 0 | 0 | 1 | 00 |
| A | JZ | 0 | 0 | 00 | 00 | 0 | 0 | 0 | 0 | 01 |
| B | JNZ | 0 | 0 | 00 | 00 | 0 | 0 | 0 | 0 | 10 |
| C | JMP | 0 | 0 | 00 | 00 | 0 | 0 | 0 | 0 | 11 |
| D–F o inválidas | Reservados | 0 | 0 | 00 | 00 | 0 | 0 | 0 | 0 | 00 |

**Importante**: el `FlagWrite` de CMP está activo aun cuando `RegWrite=0`. `MemWrite=1` exclusivamente para STORE. Los saltos **no** modifican los flags. `BranchTaken` depende además de `Z_reg` y no se incluye en la tabla fija.

## 3. Detección de instrucción válida

Definimos `op = IR[15:12]`, `Rs = IR[11:8]`, `Rd_R = IR[7:4]`, `Rd_I = IR[11:8]`, y `bajo = IR[3:0]`.

Los códigos de registro 0..3 están reservados. En 4 bits, `RegValido(x) = x[3] OR x[2]` porque los códigos de R4 a R15 tienen al menos uno de esos bits en 1.

```text
EsR = (op <= 0x7)
EsI = (op == 0x8) OR (op == 0x9)
EsJ = (op == 0xA) OR (op == 0xB) OR (op == 0xC)

ValidR = EsR AND (IR[3:0] == 0) AND RegValido(Rs) AND RegValido(Rd_R)
ValidI = EsI AND RegValido(Rd_I)
ValidJ = EsJ                         // todos los offset12 son válidos

ValidInstr = ValidR OR ValidI OR ValidJ
```

En formato R el nibble inferior **debe ser cero**; en I y J esos bits son datos válidos, y no deben comprobarse como ceros. Las instrucciones con opcodes D, E o F no están definidas.

**Política de seguridad del prototipo:** para cualquier palabra inválida, `ValidInstr=0`, todos los selectores y habilitaciones se ponen en 0, no se modifican registros/RAM/flags, y el PC avanza en una palabra. Es un tratamiento defensivo de la instrucción inválida, **no** una instrucción NOP incorporada al ISA.

## 4. Ecuaciones booleanas minimizadas a partir del opcode

Definimos `Dk = ValidInstr AND (op == k)` para `k` en hexadecimal 0..C. Por construcción, a lo sumo una salida Dk está activa.

```text
DestSel   = D8 OR D9
ALUSrc    = D9

ALUOp[1]  = D2 OR D3
ALUOp[0]  = D1 OR D3 OR D4

WBSel[1]  = D6 OR D8
WBSel[0]  = D5 OR D8

RegWrite  = D0 OR D1 OR D2 OR D3 OR D5 OR D6 OR D8 OR D9
MemRead   = D6
MemWrite  = D7
FlagWrite = D0 OR D1 OR D2 OR D3 OR D4 OR D9

BranchKind[1] = DB OR DC
BranchKind[0] = DA OR DC
BranchTaken   = DC OR (DA AND Z_reg) OR (DB AND NOT(Z_reg))
```

Estos valores implementan exactamente los controles definidos en [paso 3](03-datapath.md). Por ejemplo, `CMP` (`D4=1`) selecciona resta, activa escritura de flags y no escribe ningún registro.

## 5. Actualización del PC

```text
PCseq    = (PC + 1) mod 65536
PCbranch = (PC + sext12(IR[11:0])) mod 65536
NextPC   = BranchTaken ? PCbranch : PCseq
```

El offset es relativo al **PC de la instrucción actual**. Con `JMP 0` el PC no cambia; si un JZ no se toma, se utiliza PC+1. No se implementa delay slot. El bit `Z_reg` proviene del registro de flags, no de la salida Z instantánea de la ALU.

## 6. Reset y flanco de reloj

El decodificador es puramente combinacional y no necesita un clock. `Reset` se distribuye por fuera del módulo: mientras esté activo debe garantizarse `RegWrite_ef=RegWrite AND NOT Reset`, `MemWrite_ef=MemWrite AND NOT Reset`, `FlagWrite_ef=FlagWrite AND NOT Reset`. El registro PC y el registro flags vuelven a cero. El banco general no requiere reinicio en el ISA propuesto porque el programa debe inicializar los registros que usa. Para un reset asíncrono, elegir componentes con entrada clear apropiada; para reset síncrono, respetar la prioridad en el flanco.

## 7. Subcircuito sugerido de Logisim Evolution

**Nombre:** `CONTROL`; entradas a la izquierda: `IR[15:0]`, `Z_reg`. Salidas a la derecha: señales de la sección 1. Implementar:

1. `Splitter` de la instrucción en opcode, Rs, Rd_R y nibble bajo; reutilizar `IR[11:8]` como Rd_I.
2. Comparadores de igualdad de 4 bits para `op = 0..C`, o un `Decoder 4:16` con entradas 4 bits. No conectar múltiples salidas directamente.
3. Comparadores de nibble bajo a cero y detectores `RegValido` con OR entre los dos bits superiores del código del registro.
4. Compuertas AND/OR para `ValidR`, `ValidI`, `ValidJ` y `ValidInstr`.
5. Compuertas AND para obtener `D0..DC` **válidas**; luego las OR indicadas en la sección 4.
6. NOT de `Z_reg` y combinación AND/OR para `BranchTaken`.
7. Comprobar cada bit con probes en Logisim. No usar valores `X` o cables al aire para salidas irrelevantes: fijarlas a 0.

Una alternativa es una ROM pequeña como tabla de control por opcode, **pero la comprobación de campos inválidos y el gating de escrituras deben seguir existiendo**. Un decodificador por compuertas es más transparente para la defensa del trabajo.

## 8. Pruebas de referencia

Se agregan [`tests/unidad_control.py`](../tests/unidad_control.py) y [`tests/verificar_control.py`](../tests/verificar_control.py). El decodificador de referencia recibe IR y Z_reg y devuelve todos los selectores. La suite contrasta las 65.536 palabras de instrucción posibles para ambos valores de Z (131.072 combinaciones), además de invariantes y ejemplos dirigidos. **Ejecución local correcta (18/11/2026): 131.072 combinaciones contrastadas, de las cuales 39.168 son válidas y 91.904 inválidas; se registraron 16.384 condiciones de salto tomado.** Se comprobaron además casos dirigidos y entradas fuera de rango.

```bash
python tests/verificar_control.py
```

**Limitación:** superar las pruebas de software no verifica todavía la implementación de Logisim ni sus temporizaciones. En el paso 6 se tendrán que comprobar las salidas y el sistema completo con el circuito `.circ`.

## 9. Pendientes de la consigna 2026

- La instrucción específica que se asigne al grupo podrá ocupar uno de los opcodes D–F si su formato es compatible; no se debe activar por anticipado.
- OR inclusivo vs XOR permanece ambiguo en el texto de 2025; la unidad de control podría conservar la codificación de opcode pero requerir cambiar la función lógica de ALU.
- Convención de C en resta y flags de AND/OR: siguen siendo elecciones de diseño que deben confirmarse.
- Falta disponer de la ALU construida en clase para adaptarla materialmente a 16 bits.

## 10. Base documental

Consigna del integrador 2025; compendio de clases 1–6 de 2026 (sobre todo clases 2, 3 y 5); Resolución CD 336-25, Unidad 5 — diseño de procesadores monociclo. Los detalles de validación, seguridad ante códigos ilegales y codificación de señales son decisiones de implementación del proyecto, no exigencias textuales de esas fuentes.
