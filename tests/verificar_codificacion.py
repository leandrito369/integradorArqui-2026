"""Verificaciones mínimas del formato ISA propuesto; ejecutar con python tests/verificar_codificacion.py."""

OPCODES = {
    'ADD': 0x0, 'SUB': 0x1, 'AND': 0x2, 'OR': 0x3, 'CMP': 0x4,
    'MOV_R': 0x5, 'LOAD': 0x6, 'STORE': 0x7,
    'MOV_I': 0x8, 'ADD_I': 0x9, 'JZ': 0xA, 'JNZ': 0xB, 'JMP': 0xC,
}


def registro(r):
    if not 4 <= r <= 15:
        raise ValueError(f'Registro inválido: R{r}')
    return r


def formato_r(op, rs, rd):
    return (OPCODES[op] << 12) | (registro(rs) << 8) | (registro(rd) << 4)


def formato_i(op, rd, valor):
    if not -128 <= valor <= 127:
        raise ValueError(f'Inmediato fuera de rango: {valor}')
    return (OPCODES[op] << 12) | (registro(rd) << 8) | (valor & 0xFF)


def formato_j(op, desplazamiento):
    if not -2048 <= desplazamiento <= 2047:
        raise ValueError(f'Offset fuera de rango: {desplazamiento}')
    return (OPCODES[op] << 12) | (desplazamiento & 0xFFF)


def signo_extendido(valor, bits):
    signo = 1 << (bits - 1)
    return (valor ^ signo) - signo


assert len(OPCODES) == 13
assert formato_r('ADD', 5, 4) == 0x0540
assert formato_r('SUB', 6, 4) == 0x1640
assert formato_r('CMP', 5, 6) == 0x4560
assert formato_r('LOAD', 7, 6) == 0x6760
assert formato_r('STORE', 7, 6) == 0x7760
assert formato_i('MOV_I', 5, 100) == 0x8564
assert formato_i('MOV_I', 4, -1) == 0x84FF
assert formato_i('ADD_I', 4, 1) == 0x9401
assert formato_j('JZ', 3) == 0xA003
assert formato_j('JNZ', -2) == 0xBFFE
assert formato_j('JMP', 0) == 0xC000
assert signo_extendido(0xFF, 8) == -1
assert signo_extendido(0xFFE, 12) == -2

# Programa ilustrativo del paso 2: PC=0..12.
rom = [
    formato_i('MOV_I', 4, 0),
    formato_i('MOV_I', 5, 100),
    formato_i('MOV_I', 7, 0),
    formato_i('MOV_I', 8, 10),
    formato_r('LOAD', 7, 6),
    formato_r('CMP', 5, 6),
    formato_j('JZ', 12 - 6),
    formato_i('ADD_I', 4, 1),
    formato_i('ADD_I', 7, 1),
    formato_r('CMP', 8, 4),
    formato_j('JNZ', 4 - 10),
    formato_j('JMP', 0),
    formato_j('JMP', 0),
]
assert rom[6] == 0xA006
assert rom[10] == 0xBFFA
assert rom[-1] == 0xC000
assert len(rom) == 13
print('OK: 13 opcodes, ejemplos, extensión de signo y saltos del programa ilustrativo.')
print('ROM ilustrativa:', ' '.join(f'{v:04X}' for v in rom))
