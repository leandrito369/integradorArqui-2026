"""Modelo de referencia del datapath / ISA propuesto de 16 bits.

NO es un modelo temporal de Logisim. Una llamada a step() representa
la lógica combinacional seguida del flanco ascendente de reloj.
"""
from dataclasses import dataclass, field

MASK = 0xFFFF


def sx(x: int, bits: int) -> int:
    x &= (1 << bits) - 1
    sign = 1 << (bits - 1)
    return (x ^ sign) - sign


@dataclass
class CPU:
    rom: list[int]
    ram: list[int] = field(default_factory=lambda: [0] * 256)
    regs: dict[int, int] = field(default_factory=lambda: {r: 0 for r in range(4, 16)})
    pc: int = 0
    flags: dict[str, int] = field(default_factory=lambda: dict(Z=0, N=0, C=0, V=0))

    def step(self) -> dict:
        oldpc = self.pc
        if not 0 <= oldpc < len(self.rom):
            raise IndexError(f"PC={oldpc:04X} fuera de la ROM inicializada")
        ir = self.rom[oldpc]
        op = (ir >> 12) & 0xF
        rs = (ir >> 8) & 0xF
        rd = (ir >> 4) & 0xF if op <= 7 else rs
        immediate = sx(ir & 0xFF, 8)
        offset = sx(ir & 0xFFF, 12)
        is_r = op <= 7
        is_i = op in (8, 9)
        is_j = op in (10, 11, 12)
        valid = (is_j or
                 (is_i and 4 <= rd <= 15) or
                 (is_r and (ir & 0xF) == 0 and
                  4 <= rs <= 15 and 4 <= rd <= 15))
        trace = dict(pc=oldpc, ir=ir, opcode=op, valid=valid)
        nextpc = (oldpc + 1) & MASK
        if not valid:
            self.pc = nextpc
            trace['nextpc'] = nextpc
            return trace

        # Lecturas combinacionales antes del flanco: A siempre Rd, B siempre Rs.
        a = self.regs[rd] if not is_j else 0
        b = self.regs[rs] if is_r else 0
        result = 0
        wb = None
        dst = None
        memaddr = None
        memwrite = None
        nextflags = None

        if op in (0, 1, 2, 3, 4, 9):
            alu_b = (immediate & MASK) if op == 9 else b
            if op in (0, 9):  # ADD/ADDI
                total = a + alu_b
                result = total & MASK
                carry = int(total > MASK)
                overflow = int(bool((~(a ^ alu_b) & (a ^ result)) & 0x8000))
            elif op in (1, 4):  # SUB/CMP
                total = a + ((~alu_b) & MASK) + 1
                result = total & MASK
                # Convención propuesta de la cátedra: C=1 si hubo PRÉSTAMO.
                carry = int(not ((total >> 16) & 1))
                overflow = int(bool(((a ^ alu_b) & (a ^ result)) & 0x8000))
            elif op == 2:
                result = a & alu_b
                carry = overflow = 0
            else:
                result = a | alu_b
                carry = overflow = 0
            nextflags = dict(Z=int(result == 0), N=int(bool(result & 0x8000)),
                             C=carry, V=overflow)
            if op != 4:
                dst, wb = rd, result
        elif op == 5:  # MOV R
            dst, wb = rd, b
        elif op == 6:  # LOAD
            memaddr = b
            if not 0 <= memaddr < len(self.ram):
                raise IndexError(f"LOAD fuera de RAM: {memaddr:04X}")
            dst, wb = rd, self.ram[memaddr] & MASK
        elif op == 7:  # STORE
            memaddr = b
            if not 0 <= memaddr < len(self.ram):
                raise IndexError(f"STORE fuera de RAM: {memaddr:04X}")
            memwrite = (memaddr, a)
        elif op == 8:  # MOV I
            dst, wb = rd, immediate & MASK
        elif op in (10, 11, 12):  # JZ / JNZ / JMP
            z = self.flags['Z']  # valor almacenado al comienzo de este ciclo
            take = op == 12 or (op == 10 and z == 1) or (op == 11 and z == 0)
            if take:
                nextpc = (oldpc + offset) & MASK
            trace['branch_taken'] = take

        # Flanco de reloj: todos los cambios de estado se aplican juntos.
        if memwrite is not None:
            self.ram[memwrite[0]] = memwrite[1] & MASK
            trace['memwrite'] = memwrite
        if wb is not None:
            self.regs[dst] = wb & MASK
            trace['regwrite'] = (dst, wb & MASK)
        if nextflags is not None:
            self.flags = nextflags
            trace['flagwrite'] = nextflags.copy()
        self.pc = nextpc
        trace['nextpc'] = nextpc
        return trace
