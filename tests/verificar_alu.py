"""Comprobación de ALU16 con casos dirigidos y oráculo aritmético independiente.

Ejecutar: python tests/verificar_alu.py
"""
from random import Random

from alu_16 import OP_ADD, OP_SUB, OP_AND, OP_OR, alu16

MASK = 0xFFFF


def s16(x: int) -> int:
    return x if x < 0x8000 else x - 0x10000


def oracle(a: int, b: int, op: int) -> tuple[int, int, int, int, int]:
    if op == OP_ADD:
        zfull = a + b
        y = zfull % 65536
        c = int(zfull >= 65536)
        v = int(not -32768 <= (s16(a) + s16(b)) <= 32767)
    elif op == OP_SUB:
        y = (a - b) % 65536
        c = int(a < b)  # Préstamo (convención del grupo).
        v = int(not -32768 <= (s16(a) - s16(b)) <= 32767)
    elif op == OP_AND:
        y = a & b
        c = v = 0
    elif op == OP_OR:
        y = a | b
        c = v = 0
    else:
        raise AssertionError("OP inválido en el oráculo")
    return y, int(y == 0), int((y & 0x8000) != 0), c, v


examples = [
    (OP_ADD, 0x0001, 0x0001, (0x0002, 0, 0, 0, 0)),
    (OP_ADD, 0xFFFF, 0x0001, (0x0000, 1, 0, 1, 0)),
    (OP_ADD, 0x7FFF, 0x0001, (0x8000, 0, 1, 0, 1)),
    (OP_ADD, 0x8000, 0xFFFF, (0x7FFF, 0, 0, 1, 1)),
    (OP_SUB, 0x0000, 0x0001, (0xFFFF, 0, 1, 1, 0)),
    (OP_SUB, 0x8000, 0x0001, (0x7FFF, 0, 0, 0, 1)),
    (OP_SUB, 0x0005, 0x0005, (0x0000, 1, 0, 0, 0)),
    (OP_AND, 0xA0A0, 0x0F0F, (0x0000, 1, 0, 0, 0)),
    (OP_OR, 0x0F0F, 0xF000, (0xFF0F, 0, 1, 0, 0)),
]

checks = 0
for op, a, b, expected in examples:
    got = alu16(a, b, op)
    actual = (got.Y, got.Z, got.N, got.C, got.V)
    assert actual == expected, f"Caso dirigido: {op=} {a=:04X} {b=:04X}: {actual} != {expected}"
    checks += 1

edges = [0, 1, 2, 3, 0x7FFE, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF, 0x5555, 0xAAAA]
rng = Random(2026)
for op in (OP_ADD, OP_SUB, OP_AND, OP_OR):
    for a in edges:
        for b in edges:
            got = alu16(a, b, op)
            actual = (got.Y, got.Z, got.N, got.C, got.V)
            assert actual == oracle(a, b, op), ("frontera", op, a, b, actual, oracle(a, b, op))
            checks += 1
    for i in range(4096):
        a, b = rng.randrange(65536), rng.randrange(65536)
        got = alu16(a, b, op)
        actual = (got.Y, got.Z, got.N, got.C, got.V)
        assert actual == oracle(a, b, op), ("aleatorio", op, a, b, actual, oracle(a, b, op))
        checks += 1

for bad in (-1, 0x10000):
    try:
        alu16(bad, 0, OP_ADD)
        raise AssertionError("Operando fuera de rango aceptado")
    except ValueError:
        checks += 1
try:
    alu16(0, 0, 4)
    raise AssertionError("ALUOp fuera de rango aceptado")
except ValueError:
    checks += 1

print(f"OK: {checks} comprobaciones ALU16 (vectores dirigidos, fronteras, aleatorios y errores).")
print("Convenciones: C=préstamo en SUB; AND/OR fijan C=V=0; OR inclusivo provisional.")
