"""Modelo combinacional de la ALU de 16 bits propuesta para el integrador.

No sustituye el circuito de Logisim ni representa tiempos físicos.
La señal C de SUB es *préstamo*, no el carry-out crudo del sumador.
"""
from dataclasses import dataclass

MASK = 0xFFFF
MSB = 0x8000

OP_ADD = 0b00
OP_SUB = 0b01
OP_AND = 0b10
OP_OR = 0b11


@dataclass(frozen=True)
class ResultadoALU:
    Y: int
    Z: int
    N: int
    C: int
    V: int

    def flags(self) -> dict[str, int]:
        return {"Z": self.Z, "N": self.N, "C": self.C, "V": self.V}


def alu16(a: int, b: int, op: int) -> ResultadoALU:
    """Ejecuta combinacionalmente la operación sobre *palabras* 0..65535."""
    if not (0 <= a <= MASK and 0 <= b <= MASK):
        raise ValueError("Cada operando debe estar en el rango 0..0xFFFF")
    if op not in (OP_ADD, OP_SUB, OP_AND, OP_OR):
        raise ValueError("ALUOp inválido: usar un código de 2 bits")

    sub = int(op == OP_SUB)
    b_adder = b ^ (MASK if sub else 0)
    full_sum = a + b_adder + sub
    y_arit = full_sum & MASK
    carry_out = (full_sum >> 16) & 1

    if op == OP_ADD:
        y = y_arit
        c = carry_out
        v = int(bool((~(a ^ b) & (a ^ y)) & MSB))
    elif op == OP_SUB:
        y = y_arit
        c = 1 - carry_out  # Préstamo en resta, por convención elegida.
        v = int(bool(((a ^ b) & (a ^ y)) & MSB))
    elif op == OP_AND:
        y = a & b
        c, v = 0, 0
    else:
        y = a | b  # OR inclusivo, aún sujeto a la aclaración de la cátedra.
        c, v = 0, 0

    return ResultadoALU(Y=y, Z=int(y == 0), N=int(bool(y & MSB)), C=c, V=v)
