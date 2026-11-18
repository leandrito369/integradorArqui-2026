"""Pruebas del modelo de referencia del datapath (sin Logisim).

Ejecutar: python tests/verificar_datapath.py
"""
from simulador_datapath import CPU
from verificar_codificacion import formato_r, formato_i, formato_j, rom as rom_busqueda

count = 0


def check(condition, label):
    global count
    assert condition, label
    count += 1


def one(word, *, a=None, b=None, rd=4, rs=5, ram=None, flags=None):
    cpu = CPU(rom=[word], ram=[0] * 256 if ram is None else ram[:])
    if a is not None:
        cpu.regs[rd] = a
    if b is not None:
        cpu.regs[rs] = b
    if flags is not None:
        cpu.flags = flags.copy()
    trace = cpu.step()
    return cpu, trace


# ADD: signed overflow, carry de 16 bits, y Z.
c, t = one(formato_r('ADD', 5, 4), a=0x7FFF, b=1)
check(c.regs[4] == 0x8000 and c.flags == dict(Z=0, N=1, C=0, V=1), 'ADD overflow')
c, _ = one(formato_r('ADD', 5, 4), a=0xFFFF, b=1)
check(c.regs[4] == 0 and c.flags == dict(Z=1, N=0, C=1, V=0), 'ADD carry')

# SUB: C equivale al préstamo en esta ISA.
c, _ = one(formato_r('SUB', 5, 4), a=0, b=1)
check(c.regs[4] == 0xFFFF and c.flags == dict(Z=0, N=1, C=1, V=0), 'SUB préstamo')
c, _ = one(formato_r('SUB', 5, 4), a=0x8000, b=1)
check(c.regs[4] == 0x7FFF and c.flags['V'] == 1 and c.flags['C'] == 0, 'SUB overflow')

# Lógicas (OR inclusivo provisional) y anulación C/V.
c, _ = one(formato_r('AND', 5, 4), a=0xA0A0, b=0x0F0F)
check(c.regs[4] == 0 and c.flags == dict(Z=1, N=0, C=0, V=0), 'AND')
c, _ = one(formato_r('OR', 5, 4), a=0x0F0F, b=0xF000)
check(c.regs[4] == 0xFF0F and c.flags == dict(Z=0, N=1, C=0, V=0), 'OR')

# CMP cambia flags, no registro; además proporciona Z para JZ.
c, t = one(formato_r('CMP', 5, 4), a=100, b=100)
check(c.regs[4] == 100 and c.flags['Z'] == 1 and 'regwrite' not in t, 'CMP sin RegWrite')

# MOV registro: B->Rd; flags preservados.
f = dict(Z=1, N=1, C=1, V=1)
c, _ = one(formato_r('MOV_R', 5, 4), a=7, b=0xBEEF, flags=f)
check(c.regs[4] == 0xBEEF and c.flags == f, 'MOV registro')

# LOAD/STORE: Rs es siempre puntero y Rd el dato.
mem = [0] * 256
mem[9] = 0x1234
c, _ = one(formato_r('LOAD', 5, 4), a=99, b=9, ram=mem, flags=f)
check(c.regs[4] == 0x1234 and c.flags == f, 'LOAD indirecto')
c, t = one(formato_r('STORE', 5, 4), a=0x4321, b=9, ram=mem, flags=f)
check(c.ram[9] == 0x4321 and c.regs[4] == 0x4321 and c.flags == f and 'regwrite' not in t, 'STORE indirecto')

# Inmediatos y multiplexor de dirección Rd (IR[11:8]).
c, _ = one(formato_i('MOV_I', 6, -1), flags=f)
check(c.regs[6] == 0xFFFF and c.flags == f, 'MOV signo extendido')
c, _ = one(formato_i('ADD_I', 6, -128))
check(c.regs[6] == 0xFF80 and c.flags['N'] == 1, 'ADD inmediato con signo')

# Saltos, todos comparados contra PC actual.
c = CPU([formato_j('JZ', 2), formato_j('JMP', 0), formato_j('JMP', 0)])
c.flags['Z'] = 1
check(c.step()['nextpc'] == 2, 'JZ tomado')
c = CPU([formato_j('JZ', 2), formato_j('JMP', 0), formato_j('JMP', 0)])
c.flags['Z'] = 0
check(c.step()['nextpc'] == 1, 'JZ no tomado')
c = CPU([formato_j('JNZ', 2), formato_j('JMP', 0), formato_j('JMP', 0)])
c.flags['Z'] = 0
check(c.step()['nextpc'] == 2, 'JNZ tomado')
c = CPU([formato_j('JNZ', 2), formato_j('JMP', 0), formato_j('JMP', 0)])
c.flags['Z'] = 1
check(c.step()['nextpc'] == 1, 'JNZ no tomado')
c = CPU([formato_j('JMP', 0)])
check(c.step()['nextpc'] == 0, 'JMP 0 bucle infinito')
c = CPU([formato_j('JMP', 1), formato_j('JMP', -1)])
c.step()
check(c.step()['nextpc'] == 0, 'JMP offset negativo')

# Instrucciones con bits reservados, Rd inválido y opcode reservado:
# sin efectos secundarios (excepto avance de PC).
for invalid in (0x0541, 0x0500, 0xD000):
    c = CPU([invalid])
    before = (c.regs.copy(), c.ram[:], c.flags.copy())
    t = c.step()
    check(t['valid'] is False and c.pc == 1 and before == (c.regs, c.ram, c.flags),
          f'No efecto de instrucción inválida {invalid:04X}')

# Prueba sistémica del programa ilustrativo del paso 2.
# Se comprueba índice 0, medio, último, ausente y primer duplicado.
for idx in (0, 5, 9, None, 2):
    vec = [12, 23, 34, 45, 56, 67, 78, 89, 90, 11]
    if idx is not None:
        vec[idx] = 100
    if idx == 2:
        vec[8] = 100  # debe encontrar primero el índice 2
    c = CPU(rom=rom_busqueda, ram=vec + [0] * 246)
    pc_final = 11 if idx is None else 12
    for steps in range(200):
        if c.pc == pc_final:
            break
        c.step()
    else:
        raise AssertionError(f'Búsqueda no termina (caso índice={idx})')
    check(c.regs[4] == (10 if idx is None else idx), f'R4 al buscar idx={idx}')
    check(c.pc == pc_final and c.step()['nextpc'] == pc_final,
          f'Bucle final al buscar idx={idx}')

print(f'OK: {count} comprobaciones del datapath de referencia y búsqueda lineal.')
print('Nota: aún falta probar la ALU y el datapath en Logisim Evolution.')
