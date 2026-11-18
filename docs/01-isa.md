# Paso 1 — Especificación del ISA

**Versión:** 0.1 — 18/11/2026  
**Estado:** ISA base propuesta a partir de la consigna 2025. No es la consigna oficial 2026.

## 1. Requisitos de la consigna 2025

Se solicita un **procesador Harvard monociclo simplificado inspirado en MSP430** con PC de 16 bits, banco de 12 registros generales R4–R15, ALU de 16 bits, ROM de instrucciones de 16 bits por palabra, RAM de datos de 16 bits por palabra, unidad de control y flags Z/N/C/V. Operaciones en complemento a dos. La ALU debe adaptar la desarrollada previamente en clases a 16 bits. Debe implementarse en Logisim Evolution.

La consigna exige el programa de búsqueda lineal del valor 100 en un array de 10 palabras alojado a partir de RAM[0]. Si se encuentra, el índice debe quedar en R4; el programa debe finalizar con un bucle infinito tanto si encuentra el valor como si no.

Las fases FETCH, DECODE, EXECUTE, MEMORY y WRITE-BACK son **operaciones combinacionales dentro del mismo ciclo**; no son etapas de pipeline.

## 2. Decisiones de diseño del grupo (propuestas)

| Parámetro | Decisión | Justificación |
|---|---|---|
| Instrucciones | Una palabra de 16 bits | Simplifica ROM y PC |
| Memorias | ROM y RAM separadas, direccionables por palabra | Coincide con array de palabras y evita lógica de direccionamiento por byte |
| PC | 16 bits, reset en 0 | ROM comienza en la primera palabra |
| Secuencia | PC_siguiente = PC_actual + 1 | Una instrucción por dirección de palabra |
| Salto tomado | PC_siguiente = PC_actual + sext(offset) | La consigna dice PC = PC + offset |
| Salto no tomado | PC_siguiente = PC_actual + 1 | Continuidad secuencial |
| Bucle infinito | `JMP 0` | Retiene PC actual |
| Registros | R4…R15, 16 bits cada uno | Los códigos de 4 bits 0…3 están reservados |
| Datos | Complemento a dos, 16 bits | Rango firmado -32768…32767 |
| E/S, interrupciones | Fuera de alcance | No figuran en requisitos 2025 |

Las direcciones fuera de la capacidad física de ROM/RAM y los códigos ilegales deberán definirse en el datapath y la unidad de control. La capacidad concreta N/M no está fijada por la consigna.

## 3. Conjunto de instrucciones (13)

La notación del enunciado usa **fuente primero, destino segundo**.

| Instrucción | Comportamiento |
|---|---|
| `ADD Rs, Rd` | `Rd ← (Rd + Rs) mod 65536` |
| `SUB Rs, Rd` | `Rd ← (Rd - Rs) mod 65536` |
| `AND Rs, Rd` | `Rd ← Rd & Rs` |
| `OR Rs, Rd` | `Rd ← Rd \| Rs` (provisional; ver ambigüedad) |
| `CMP Rs, Rd` | Resta `Rd-Rs`, **solo flags**, no escribe registro |
| `MOV Rs, Rd` | `Rd ← Rs` |
| `MOV @Rs, Rd` | `Rd ← RAM[Rs]` |
| `MOV Rd, @Rs` | `RAM[Rs] ← Rd` |
| `MOV #imm, Rd` | `Rd ← sext(imm)` |
| `ADD #imm, Rd` | `Rd ← (Rd + sext(imm)) mod 65536` |
| `JZ offset` | Si Z=1, salta relativo al PC actual; si no, PC+1 |
| `JNZ offset` | Si Z=0, salta relativo al PC actual; si no, PC+1 |
| `JMP offset` | Salta incondicionalmente relativo al PC actual |

**Ambigüedad de la consigna:** para `OR` aparece la expresión `Rd = Rd ^ Rs`. `^` comúnmente indica XOR, pero `OR` significa OR inclusivo. **Interpretación provisional:** OR inclusivo; verificar con la cátedra antes de considerarlo definitivo.

## 4. Modos de direccionamiento

- **Registro:** `ADD R5, R4`.
- **Indirecto por registro:** `MOV @R7, R6` carga `RAM[R7]`; `MOV R6, @R7` almacena en `RAM[R7]`.
- **Inmediato con signo:** `MOV #100, R5`.
- **Relativo al PC actual:** `JNZ -2` retrocede dos posiciones de instrucción cuando Z=0.

## 5. Flags: propuesta de semántica

- `Z=1` si el resultado de 16 bits es cero.
- `N=result[15]` (bit de signo).
- Para **suma**, `C=carry_out` del bit 15; para **resta y CMP**, `C=1` si se produjo **préstamo**, por lo tanto `C=NOT(carry_out)` del sumador `A + ~B + 1`.
- `V=1` cuando el resultado firmado desborda el rango de 16 bits; distinto de C.

Se propone que `ADD`, `SUB`, `CMP`, `ADD #imm` actualicen Z/N/C/V. `AND` y `OR` actualizan Z/N y fijan C/V en 0. `MOV`, LOAD, STORE y saltos preservan los flags.

Para suma con `A=Rd`, `B=Rs` o inmediato: `V = NOT(A15 XOR B15) AND (A15 XOR resultado15)`.
Para resta: `V = (A15 XOR B15) AND (A15 XOR resultado15)`.

**Pendiente de confirmación:** algunas ISA usan C=1 para *ausencia* de préstamo, y la política de flags de operaciones lógicas no está especificada en el enunciado. Las reglas anteriores son elecciones justificadas, no normas aseguradas de la cátedra.

## 6. Prueba funcional que debe poder resolver

Uso recomendado de registros: R4 índice (0–9 si encuentra; 10 como centinela si no encuentra), R5 constante 100, R6 dato actual, R7 puntero a RAM, R8 longitud 10. El repertorio incluye todo lo necesario: inicializar inmediatos, LOAD, comparar, incrementar índice/puntero, bifurcar y finalizar con `JMP 0`.

## 7. Temas pendientes

- Revisión de la instrucción adicional que asigne la cátedra en 2026.
- Confirmación OR/XOR y comportamiento de flags.
- Elección N/M y semántica de accesos fuera de rango.
- Implementación del circuito previo de ALU exigido por el docente.
- Definición y validación de formatos binarios en [Paso 2](02-formatos-instrucciones.md).

## 8. Fuentes de trabajo

1. Consigna "Integrador de Arquitectura de Computadoras - 2025".
2. "Arquitectura de Computadoras — Compendio Teórico (Clases 1 a 6)", especialmente clases 1–3 y 5–6.
3. "Resolución CD 336-25", programa analítico 2026–2029 (unidad de diseño de procesadores de ciclo único).
