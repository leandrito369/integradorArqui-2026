# Paso 4 — ALU de 16 bits y flags

**Estado:** diseño funcional verificado en Python; pendiente implementación y validación en Logisim Evolution. Basado en la consigna 2025 y los [pasos 1–3](03-datapath.md).

## Requisitos y decisiones de diseño

La consigna exige una ALU de 16 bits en complemento a dos que adapte la desarrollada en clases, más los flags Z, N, C y V. La ALU concreta de las clases aún no fue suministrada: este documento fija la interfaz y la lógica requerida, pero no certifica la reutilización del circuito original.

| ALUOp | Operación | Resultado (16 bits) | Instrucciones |
| --- | --- | --- | --- |
| `00` | ADD | `(A+B) & 0xFFFF` | ADD R, ADD #imm |
| `01` | SUB | `(A-B) & 0xFFFF` | SUB R, CMP |
| `10` | AND | `A & B` | AND R |
| `11` | OR | `A \| B` | OR R, provisional |

`A=ReadA=Rd`, `B=ALUSrc ? signo_extendido(imm8) : ReadB`. El resultado de CMP se usa solo para flags; nunca se escribe en Rd (`RegWrite=0`, `FlagWrite=1`).

## Sumador-restador compartido

Se propone un sumador de 16 bits y 16 compuertas XOR para invertir B cuando la operación es SUB:

```text
Sub = (ALUOp == 01)
B_mod[i] = B[i] XOR Sub           (i=0..15)
C0 = Sub
S17 = zero_extend(A) + zero_extend(B_mod) + C0
Y_arit = S17[15:0]
CarryOut = S17[16]
```

Cada full-adder de un sumador ripple-carry puede expresarse con `P_i=A_i XOR B_mod_i`, `S_i=P_i XOR C_i` y `C_(i+1)=(A_i AND B_mod_i) OR (P_i AND C_i)`. Un MUX de 4 entradas de 16 bits selecciona `Y_arit`, `Y_and=A AND B` y `Y_or=A OR B` según ALUOp.

## Flags (resultados combinacionales)

| Flag | Ecuación |
| --- | --- |
| Z | `1 si Y==0; 0 si no` |
| N | `Y[15]` (bit de signo del resultado truncado) |
| C en ADD | `CarryOut` |
| C en SUB | `NOT CarryOut`, equivalente a `A_unsigned < B_unsigned` (1 = hubo préstamo) |
| C en AND/OR | `0` (decisión del grupo) |
| V en ADD | `NOT(a XOR b) AND (a XOR r)` |
| V en SUB | `(a XOR b) AND (a XOR r)` |
| V en AND/OR | `0` (decisión del grupo) |

En estas ecuaciones `a=A[15]`, `b=B[15]` y `r=Y[15]`. En ADD/SUB es equivalente `V=C15 XOR C16` sobre el sumador-restador. **Carry/préstamo y overflow con signo son conceptos distintos.**

## Registro de flags

La ALU debe ser **combinacional**. Sus cuatro salidas Z/N/C/V entran a un registro de 4 bits habilitado por `FlagWrite`, con el mismo flanco ascendente de reloj que PC y banco de registros. Reset propuesto: Z=N=C=V=0.

| Instrucciones | FlagWrite | RegWrite |
| --- | --- | --- |
| ADD, SUB, AND, OR, ADD #imm | 1 | 1 |
| CMP | 1 | 0 |
| MOV R, LOAD, MOV #imm | 0 | 1 |
| STORE, JZ, JNZ, JMP e inválidas | 0 | 0 |

Los saltos consultan **Z almacenado**, no el resultado combinacional del mismo ciclo. Los movimientos y saltos preservan todos los flags anteriores.

## Vectores de referencia

| Op | A | B | Y | ZNCV |
| --- | --- | --- | --- | --- |
| ADD | `0001` | `0001` | `0002` | `0000` |
| ADD | `FFFF` | `0001` | `0000` | `1010` |
| ADD | `7FFF` | `0001` | `8000` | `0101` |
| ADD | `8000` | `FFFF` | `7FFF` | `0011` |
| SUB | `0000` | `0001` | `FFFF` | `0110` |
| SUB | `8000` | `0001` | `7FFF` | `0001` |
| SUB | `0005` | `0005` | `0000` | `1000` |
| AND | `A0A0` | `0F0F` | `0000` | `1000` |
| OR | `0F0F` | `F000` | `FF0F` | `0100` |

Los hexadecimales no llevan prefijo 0x en esta tabla. `ZNCV` se presenta en ese orden.

## Validación

Se incorporan `tests/alu_16.py` y `tests/verificar_alu.py`. Las pruebas verifican las operaciones y flags ante casos límite y 4.096 pares aleatorios reproducibles por operación, contrastados con un oráculo aritmético independiente. Resultado local: **16.972 comprobaciones correctas**. Esto no reemplaza la prueba en Logisim.

## Ambigüedades pendientes

1. La consigna escribe `OR`, pero muestra `^`: aquí OR inclusivo es **provisional**; podría ser XOR.
2. La consigna describe C como acarreo/préstamo, pero no fija una convención eléctrica; se usa `C=1` cuando hubo préstamo en SUB.
3. AND/OR fijan C y V en cero por decisión de diseño; la cátedra debe confirmarlo.
4. Se necesita el archivo de la ALU original de clases para cumplir literalmente la exigencia de adaptación a 16 bits.

**Fuentes:** integrador 2025; apuntes de clases 1–3 (complemento a dos, compuertas, registros síncronos), clase 5 (ISA); Resolución CD 336/25 (Unidad 5).
