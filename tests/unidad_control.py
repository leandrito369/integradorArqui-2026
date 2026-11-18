"""Decodificador combinacional de referencia para el ISA Harvard monociclo 16-bit.

La unidad de control REAL se implementará con componentes de Logisim Evolution.
Este modelo es independiente de relojes: la función solo calcula señales a
partir de la instrucción actual y de Z previamente almacenado.
"""
from typing import NamedTuple


class SenalesControl(NamedTuple):
    ValidInstr: int
    DestSel: int
    ALUSrc: int
    ALUOp: int
    WBSel: int
    RegWrite: int
    MemRead: int
    MemWrite: int
    FlagWrite: int
    BranchKind: int
    BranchTaken: int


def reg_valido(codigo: int) -> bool:
    """R4..R15 válidos: OR de los bits 3 y 2 del campo de 4 bits."""
    if not 0 <= codigo <= 0xF:
        return False
    return bool(codigo & 0b1100)


def decodificar_control(ir: int, z_reg: int) -> SenalesControl:
    """Calcula salidas deterministas desde IR de 16 bits y Z almacenado."""
    if not isinstance(ir, int) or not 0 <= ir <= 0xFFFF:
        raise ValueError("IR debe ser una palabra de 16 bits")
    if z_reg not in (0, 1):
        raise ValueError("Z_reg debe ser 0 o 1")

    op = (ir >> 12) & 0xF
    rs = (ir >> 8) & 0xF
    rd_r = (ir >> 4) & 0xF
    rd_i = rs
    nibble_bajo = ir & 0xF

    es_r = op <= 7
    es_i = op in (8, 9)
    es_j = op in (10, 11, 12)
    valido_r = es_r and nibble_bajo == 0 and reg_valido(rs) and reg_valido(rd_r)
    valido_i = es_i and reg_valido(rd_i)
    valido_j = es_j
    valido = bool(valido_r or valido_i or valido_j)

    # Cada Di ya incluye la validación de campos. Ante IR ilegal Di=0.
    d = [int(valido and op == k) for k in range(13)]

    return SenalesControl(
        ValidInstr=int(valido),
        DestSel=int(bool(d[8] or d[9])),
        ALUSrc=d[9],
        ALUOp=(int(bool(d[2] or d[3])) << 1) | int(bool(d[1] or d[3] or d[4])),
        WBSel=(int(bool(d[6] or d[8])) << 1) | int(bool(d[5] or d[8])),
        RegWrite=int(bool(d[0] or d[1] or d[2] or d[3] or
                          d[5] or d[6] or d[8] or d[9])),
        MemRead=d[6],
        MemWrite=d[7],
        FlagWrite=int(bool(d[0] or d[1] or d[2] or d[3] or d[4] or d[9])),
        BranchKind=(int(bool(d[11] or d[12])) << 1) | int(bool(d[10] or d[12])),
        BranchTaken=int(bool(d[12] or (d[10] and z_reg) or
                             (d[11] and not z_reg))),
    )
