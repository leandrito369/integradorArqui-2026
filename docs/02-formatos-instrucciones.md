# Paso 2 — Formatos de instrucciones y codificación

**Versión:** 0.1 — 18/11/2026  
**Estado:** diseño propuesto para la ISA base del [paso 1](01-isa.md); pendiente de validación de la consigna 2026 y del circuito Logisim.

## 1. Restricciones y criterio de diseño

Hay **13 operaciones**, de modo que un campo `opcode` de **4 bits** (16 valores) alcanza y deja **3 códigos libres**. Los 12 registros generales R4…R15 también requieren campos de **4 bits**, conservando su valor numérico de 4 a 15. Todas las instrucciones ocupan **una palabra de 16 bits** y no hay palabras de extensión.

Se diseñan tres formatos, sin campos de función adicionales:

- **R (registro/registro y memoria indirecta):** `opcode[15:12] | Rs[11:8] | Rd[7:4] | 0000[3:0]`.
- **I (inmediato):** `opcode[15:12] | Rd[11:8] | imm8[7:0]`.
- **J (salto):** `opcode[15:12] | offset12[11:0]`.

La ubicación de `Rd` **no es constante entre R e I**: simplificamos la extensión del inmediato de 8 bits y asumimos un multiplexor de selección de registro destino. Es una decisión de compromiso documentada. En el formato R, los bits 3:0 deben ser cero (como exige la consigna para bits sin uso).

## 2. Tabla completa de opcodes

| Opcode (hex) | Binario | Instrucción | Formato | Significado |
|---|---|---|---|---|
| `0` | `0000` | `ADD Rs, Rd` | R | Rd ← Rd + Rs |
| `1` | `0001` | `SUB Rs, Rd` | R | Rd ← Rd - Rs |
| `2` | `0010` | `AND Rs, Rd` | R | Rd ← Rd & Rs |
| `3` | `0011` | `OR Rs, Rd` | R | Rd ← Rd \| Rs (provisional) |
| `4` | `0100` | `CMP Rs, Rd` | R | Flags de Rd - Rs; sin escritura |
| `5` | `0101` | `MOV Rs, Rd` | R | Rd ← Rs |
| `6` | `0110` | `MOV @Rs, Rd` | R | Rd ← RAM[Rs] |
| `7` | `0111` | `MOV Rd, @Rs` | R | RAM[Rs] ← Rd |
| `8` | `1000` | `MOV #imm, Rd` | I | Rd ← sext(imm8) |
| `9` | `1001` | `ADD #imm, Rd` | I | Rd ← Rd + sext(imm8) |
| `A` | `1010` | `JZ offset` | J | Salta si Z=1 |
| `B` | `1011` | `JNZ offset` | J | Salta si Z=0 |
| `C` | `1100` | `JMP offset` | J | Salto incondicional |
| `D`–`F` | `1101`–`1111` | Reservados | — | Sin comportamiento definido todavía |

### Particularidad de LOAD/STORE

`Rs` (bits 11:8) contiene **siempre el registro de dirección RAM** en ambas operaciones. `Rd` (bits 7:4) contiene el registro de datos: destino en LOAD, fuente en STORE. El ensamblador debe preservar la sintaxis `MOV Rd, @Rs` del enunciado.

## 3. Valores inmediatos y offset

- `imm8`: 8 bits en complemento a dos, alcance **-128 a +127**. `sext8(imm8)` replica el bit 7 en los ocho bits superiores. Por ejemplo, `100 = 0x64` cabe directamente; `-1 = 0xFF` se extiende a `0xFFFF`.
- `offset12`: 12 bits en complemento a dos, alcance **-2048 a +2047** instrucciones. `sext12(offset12)` replica el bit 11 en los cuatro bits superiores.
- Para un salto a la etiqueta `L` desde instrucción ubicada en posición `P`: **`offset = L - P`**, no `L - (P + 1)`. El salto con offset cero mantiene el PC apuntando a esa misma instrucción.
- Se rechazan fuera de rango los inmediatos y desplazamientos en el futuro ensamblador; **no** se truncan silenciosamente.
- Los valores de **16 bits completos no caben en un `MOV #imm, Rd`**. Se pueden construir mediante una secuencia de instrucciones (por ejemplo, acumulación y duplicación con `ADD Rn, Rn`); no se deben fingir inmediatos de 16 bits en un único word.

## 4. Ejemplos de codificación exacta

| Ensamblador | Campos | Hex (16 bits) | Binario |
|---|---|---|---|
| `ADD R5, R4` | 0 · 5 · 4 · 0 | `0x0540` | `0000 0101 0100 0000` |
| `SUB R6, R4` | 1 · 6 · 4 · 0 | `0x1640` | `0001 0110 0100 0000` |
| `CMP R5, R6` | 4 · 5 · 6 · 0 | `0x4560` | `0100 0101 0110 0000` |
| `MOV @R7, R6` | 6 · 7 · 6 · 0 | `0x6760` | `0110 0111 0110 0000` |
| `MOV R6, @R7` | 7 · 7 · 6 · 0 | `0x7760` | `0111 0111 0110 0000` |
| `MOV #100, R5` | 8 · 5 · 64 | `0x8564` | `1000 0101 0110 0100` |
| `MOV #-1, R4` | 8 · 4 · FF | `0x84FF` | `1000 0100 1111 1111` |
| `ADD #1, R4` | 9 · 4 · 01 | `0x9401` | `1001 0100 0000 0001` |
| `JZ +3` | A · 003 | `0xA003` | `1010 0000 0000 0011` |
| `JNZ -2` | B · FFE | `0xBFFE` | `1011 1111 1111 1110` |
| `JMP 0` | C · 000 | `0xC000` | `1100 0000 0000 0000` |

Todos los ejemplos son **codificaciones de nuestro ISA propuesto**, no códigos máquina MSP430 ni RISC-V.

## 5. Ejemplo de programa viable con esta codificación

Este ejemplo valida la capacidad del repertorio, **no reemplaza** el programa de entrega del paso 7. Se supone RAM[0..9] precargada con diez palabras. Las etiquetas corresponden a direcciones de ROM de una palabra.

```asm
; PC      Instrucción           Propósito
; 0       MOV #0, R4           índice = 0
; 1       MOV #100, R5         objetivo = 100
; 2       MOV #0, R7           puntero = 0
; 3       MOV #10, R8          límite = 10
buscar:
; 4       MOV @R7, R6         leer RAM[puntero]
; 5       CMP R5, R6          comparar valor y objetivo
; 6       JZ encontrado       si iguales, dejar R4 con índice
; 7       ADD #1, R4          índice++
; 8       ADD #1, R7          puntero++
; 9       CMP R8, R4          comparar índice con 10
; 10      JNZ buscar          si aún quedan, repetir
fin:
; 11      JMP fin             caso no encontrado: R4 = 10
encontrado:
; 12      JMP encontrado      caso encontrado: R4 = posición 0..9
```

**Offset de `JZ encontrado` en PC=6:** `12 - 6 = +6` → `0xA006`.

**Offset de `JNZ buscar` en PC=10:** `4 - 10 = -6` → `0xBFFA`.

**Bucles finales:** PC=11 y PC=12 usan ambos `JMP 0` → `0xC000`.

Es necesario validar contra el comportamiento acordado de `CMP` (flags de Rd-Rs). La comparación de igualdad depende solo de Z, por lo cual el orden de los operandos no altera el resultado de igualdad.

## 6. Consecuencias para el datapath (paso 3)

La unidad de control tendrá que seleccionar el registro destino entre `IR[7:4]` (formato R) y `IR[11:8]` (formato I). Los dos puertos de lectura del banco accederán a `Rs` y `Rd` para las instrucciones R, y a `Rd` + inmediato para `ADD #imm`. En LOAD/STORE se debe encaminar el valor de Rs a la dirección RAM y el valor de Rd como dato de escritura en STORE. El decodificador usará `IR[15:12]`; habrá un extensor de signo `imm8`, otro `offset12`, un sumador de PC+1 y otro de PC+offset (o una ALU compartida si el camino lo permite). Las instrucciones no válidas y campos reservados deberán tratarse de forma explícita.

## 7. Pendientes de validación

1. Confirmar si el docente pretende OR inclusivo o XOR.
2. Confirmar política de flags y carry/borrow.
3. Confirmar o ajustar el nuevo opcode o instrucción extra asignada en 2026.
4. Elegir un comportamiento seguro para codificaciones reservadas (p. ej., sin escrituras y PC+1), indicando que es decisión de diseño y no una instrucción adicional.
