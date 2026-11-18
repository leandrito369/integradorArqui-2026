"""Suite exhaustiva del decodificador de control 16-bit.

Ejecutar desde raíz: python tests/verificar_control.py
Compara TODAS las palabras IR=0..65535 con Z=0 y Z=1 (131072 casos)
frente a tabla de control y reglas de validez independientes del modelo.
"""
from unidad_control import SenalesControl, decodificar_control

# Cada tupla representa:
# DestSel, ALUSrc, ALUOp, WBSel, RegWrite,
# MemRead, MemWrite, FlagWrite, BranchKind
TABLA = {
    0x0: (0, 0, 0, 0, 1, 0, 0, 1, 0),  # ADD
    0x1: (0, 0, 1, 0, 1, 0, 0, 1, 0),  # SUB
    0x2: (0, 0, 2, 0, 1, 0, 0, 1, 0),  # AND
    0x3: (0, 0, 3, 0, 1, 0, 0, 1, 0),  # OR
    0x4: (0, 0, 1, 0, 0, 0, 0, 1, 0),  # CMP
    0x5: (0, 0, 0, 1, 1, 0, 0, 0, 0),  # MOV reg
    0x6: (0, 0, 0, 2, 1, 1, 0, 0, 0),  # LOAD
    0x7: (0, 0, 0, 0, 0, 0, 1, 0, 0),  # STORE
    0x8: (1, 0, 0, 3, 1, 0, 0, 0, 0),  # MOV imm
    0x9: (1, 1, 0, 0, 1, 0, 0, 1, 0),  # ADD imm
    0xA: (0, 0, 0, 0, 0, 0, 0, 0, 1),  # JZ
    0xB: (0, 0, 0, 0, 0, 0, 0, 0, 2),  # JNZ
    0xC: (0, 0, 0, 0, 0, 0, 0, 0, 3),  # JMP
}


def oraculo(ir: int, z: int) -> SenalesControl:
    """Oráculo tabular: no utiliza las ecuaciones booleanas del decodificador."""
    op = ir >> 12
    rs_o_rd_i = (ir >> 8) & 0xF
    rd_r = (ir >> 4) & 0xF
    if op in range(8):
        legal = rs_o_rd_i >= 4 and rd_r >= 4 and ir % 16 == 0
    elif op in (8, 9):
        legal = rs_o_rd_i >= 4
    else:
        legal = op in (10, 11, 12)

    if not legal:
        return SenalesControl(*([0] * 11))

    datos = TABLA[op]
    salto = int(
        op == 12 or
        (op == 10 and z == 1) or
        (op == 11 and z == 0)
    )
    return SenalesControl(1, *datos, salto)


assert len(TABLA) == 13
casos = 0
validos = 0
invalidos = 0
saltos_tomados = 0

for ir in range(65536):
    for z in (0, 1):
        obtenido = decodificar_control(ir, z)
        esperado = oraculo(ir, z)
        assert obtenido == esperado, (
            f"IR={ir:04X}, Z={z}\nobtenido={obtenido}\nesperado={esperado}"
        )
        assert not (obtenido.RegWrite and obtenido.MemWrite), f"doble escritura IR={ir:04X}"
        assert not (obtenido.MemWrite and obtenido.FlagWrite), f"STORE modifica flags IR={ir:04X}"
        assert not (obtenido.BranchTaken and obtenido.BranchKind == 0), f"salto no-J IR={ir:04X}"
        if not obtenido.ValidInstr:
            assert sum(obtenido) == 0, f"efecto de opcode inválido IR={ir:04X}"
            invalidos += 1
        else:
            validos += 1
        saltos_tomados += obtenido.BranchTaken
        casos += 1

# Casos de regresión que vinculan el decoder a palabras concretas del ISA.
ejemplos = {
    0x0540: ("ADD R5,R4", 0, 0, 1, 0, 1),
    0x1640: ("SUB R6,R4", 1, 0, 1, 0, 1),
    0x4560: ("CMP R5,R6", 1, 0, 0, 0, 1),
    0x6760: ("LOAD @R7,R6", 0, 2, 1, 0, 0),
    0x7760: ("STORE R6,@R7", 0, 0, 0, 1, 0),
    0x8564: ("MOV #100,R5", 0, 3, 1, 0, 0),
    0x9401: ("ADD #1,R4", 0, 0, 1, 0, 1),
}
for ir, (nombre, alu, wb, rw, mw, fw) in ejemplos.items():
    out = decodificar_control(ir, 0)
    assert out.ValidInstr
    assert (out.ALUOp, out.WBSel, out.RegWrite, out.MemWrite, out.FlagWrite) == (alu, wb, rw, mw, fw), nombre

# Saltos relativos: el decodificador jamás ejecuta efectos secundarios.
for ir, branch_for_z0, branch_for_z1 in (
    (0xA006, 0, 1),   # JZ +6
    (0xBFFA, 1, 0),   # JNZ -6
    (0xC000, 1, 1),   # JMP 0
):
    assert decodificar_control(ir, 0).BranchTaken == branch_for_z0
    assert decodificar_control(ir, 1).BranchTaken == branch_for_z1

# Entradas fuera de contrato; el hardware tendrá solo 16 bits y un flag.
for ir, z in ((-1, 0), (65536, 0), (0, -1), (0, 2)):
    try:
        decodificar_control(ir, z)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Entrada fuera de rango aceptada {ir=}, {z=}")

print(f"OK: {casos:,} combinaciones IR/Z contrastadas con tabla independiente")
print(f"Válidas: {validos:,}; inválidas: {invalidos:,}; saltos tomados: {saltos_tomados:,}.")
print("Además: invariantes de escritura, casos reales de codificación y errores de entrada.")
