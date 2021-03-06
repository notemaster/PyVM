from ..debug import debug
from ..Registers import Reg32
from ..util import Instruction, to_int, byteorder
from ..misc import parity, Shift

from functools import partialmethod as P
import operator

MAXVALS = [None, (1 << 8) - 1, (1 << 16) - 1, None, (1 << 32) - 1]  # MAXVALS[n] is the maximum value of an unsigned n-bit number
SIGNS   = [None, 1 << 8 - 1, 1 << 16 - 1, None, 1 << 32 - 1]  # SIGNS[n] is the maximum absolute value of a signed n-bit number

####################
# AND / OR / XOR / TEST
####################
class BITWISE(Instruction):
    """
    Perform a bitwise operation.
    Flags:
        OF, CF cleared
        SF, ZF, PF set according to the result
        AF undefined

    Operation: c <- a [op] b

    :param test: whether the instruction to be executed is TEST
    """

    def __init__(self):
        self.opcodes = {
            # AND
            0x24: P(self.r_imm, _8bit=True, operation=operator.and_),
            0x25: P(self.r_imm, _8bit=False, operation=operator.and_),

            0x80: [
                P(self.rm_imm, _8bit=True, _8bit_imm=True, operation=operator.and_),
                P(self.rm_imm, _8bit=True, _8bit_imm=True, operation=operator.or_),
                P(self.rm_imm, _8bit=True, _8bit_imm=True, operation=operator.xor)
                ],
            0x81: [
                P(self.rm_imm, _8bit=False, _8bit_imm=False, operation=operator.and_),
                P(self.rm_imm, _8bit=False, _8bit_imm=False, operation=operator.or_),
                P(self.rm_imm, _8bit=False, _8bit_imm=False, operation=operator.xor)
                ],
            0x83: [
                P(self.rm_imm, _8bit=False, _8bit_imm=True, operation=operator.and_),
                P(self.rm_imm, _8bit=False, _8bit_imm=True, operation=operator.or_),
                P(self.rm_imm, _8bit=False, _8bit_imm=True, operation=operator.xor)
                ],

            0x20: P(self.rm_r, _8bit=True, operation=operator.and_),
            0x21: P(self.rm_r, _8bit=False, operation=operator.and_),

            0x22: P(self.r_rm, _8bit=True, operation=operator.and_),
            0x23: P(self.r_rm, _8bit=False, operation=operator.and_),

            # OR
            0x0C: P(self.r_imm, _8bit=True, operation=operator.or_),
            0x0D: P(self.r_imm, _8bit=False, operation=operator.or_),

            0x08: P(self.rm_r, _8bit=True, operation=operator.or_),
            0x09: P(self.rm_r, _8bit=False, operation=operator.or_),

            0x0A: P(self.r_rm, _8bit=True, operation=operator.or_),
            0x0B: P(self.r_rm, _8bit=False, operation=operator.or_),

            # XOR
            0x34: P(self.r_imm, _8bit=True, operation=operator.xor),
            0x35: P(self.r_imm, _8bit=False, operation=operator.xor),

            0x30: P(self.rm_r, _8bit=True, operation=operator.xor),
            0x31: P(self.rm_r, _8bit=False, operation=operator.xor),

            0x32: P(self.r_rm, _8bit=True, operation=operator.xor),
            0x33: P(self.r_rm, _8bit=False, operation=operator.xor),

            # TEST
            0xA8: P(self.r_imm, _8bit=True, operation=operator.and_, test=True),
            0xA9: P(self.r_imm, _8bit=False, operation=operator.and_, test=True),

            0xF6: P(self.rm_imm, _8bit=True, _8bit_imm=True, operation=operator.and_, test=True),
            0xF7: P(self.rm_imm, _8bit=False, _8bit_imm=False, operation=operator.and_, test=True),

            0x84: P(self.rm_r, _8bit=True, operation=operator.and_, test=True),
            0x85: P(self.rm_r, _8bit=False, operation=operator.and_, test=True),
            }

    def r_imm(vm, _8bit, operation, test=False) -> True:
        sz = 1 if _8bit else vm.operand_size
        b = vm.mem.get(vm.eip, sz)
        vm.eip += sz
        b = to_int(b)

        a = to_int(vm.reg.get(0, sz))

        vm.reg.eflags_set(Reg32.OF, 0)
        vm.reg.eflags_set(Reg32.CF, 0)

        c = operation(a, b)

        vm.reg.eflags_set(Reg32.SF, (c >> (sz * 8 - 1)) & 1)

        c &= MAXVALS[sz]

        vm.reg.eflags_set(Reg32.ZF, c == 0)

        c = c.to_bytes(sz, byteorder)

        vm.reg.eflags_set(Reg32.PF, parity(c[0], sz))

        if not test:
            name = operation.__name__
            vm.reg.set(0, c)
        else:
            name = 'test'

        if debug: print('{} {}, imm{}({})'.format(name, [0, 'al', 'ax', 0, 'eax'][sz], sz * 8, b))

        return True

    def rm_imm(vm, _8bit, _8bit_imm, operation, test=False) -> bool:
        sz = 1 if _8bit else vm.operand_size
        imm_sz = 1 if _8bit_imm else vm.operand_size
        old_eip = vm.eip

        RM, R = vm.process_ModRM(sz, sz)

        if (operation == operator.and_):
            if (not test) and (R[1] != 4):
                vm.eip = old_eip
                return False  # this is not AND
            elif test and (R[1] != 0):
                vm.eip = old_eip
                return False  # this is not TEST
        elif (operation == operator.or_) and (R[1] != 1):
            vm.eip = old_eip
            return False  # this is not OR
        elif (operation == operator.xor) and (R[1] != 6):
            vm.eip = old_eip
            return False  # this is not XOR

        b = vm.mem.get(vm.eip, imm_sz)
        vm.eip += imm_sz
        b = sign_extend(b, sz)
        b = to_int(b)

        type, loc, _ = RM

        vm.reg.eflags_set(Reg32.OF, 0)
        vm.reg.eflags_set(Reg32.CF, 0)

        a = to_int((vm.mem if type else vm.reg).get(loc, sz))
        c = operation(a, b)

        vm.reg.eflags_set(Reg32.SF, (c >> (sz * 8 - 1)) & 1)

        c &= MAXVALS[sz]

        vm.reg.eflags_set(Reg32.ZF, c == 0)

        c = c.to_bytes(sz, byteorder)

        vm.reg.eflags_set(Reg32.PF, parity(c[0], sz))

        if not test:
            name = operation.__name__
            (vm.mem if type else vm.reg).set(loc, c)
        else:
            name = 'test'

        if debug: print('{0} {5}{1}({2}),imm{3}({4})'.format(name, sz * 8, loc, imm_sz * 8, b, ('m' if type else 'r')))

        return True

    def rm_r(vm, _8bit, operation, test=False) -> True:
        sz = 1 if _8bit else vm.operand_size
        RM, R = vm.process_ModRM(sz, sz)

        type, loc, _ = RM

        vm.reg.eflags_set(Reg32.OF, 0)
        vm.reg.eflags_set(Reg32.CF, 0)

        a = to_int((vm.mem if type else vm.reg).get(loc, sz))
        b = to_int(vm.reg.get(R[1], sz))

        c = operation(a, b)

        vm.reg.eflags_set(Reg32.SF, (c >> (sz * 8 - 1)) & 1)

        c &= MAXVALS[sz]

        vm.reg.eflags_set(Reg32.ZF, c == 0)

        c = c.to_bytes(sz, byteorder)

        vm.reg.eflags_set(Reg32.PF, parity(c[0], sz))

        if not test:
            name = operation.__name__
            (vm.mem if type else vm.reg).set(loc, c)
        else:
            name = 'test'

        if debug: print('{0} {4}{1}({2}),r{1}({3})'.format(name, sz * 8, loc, R[1], ('m' if type else '_r')))

        return True

    def r_rm(vm, _8bit, operation, test=False) -> True:
        sz = 1 if _8bit else vm.operand_size
        RM, R = vm.process_ModRM(sz, sz)

        type, loc, _ = RM

        vm.reg.eflags_set(Reg32.OF, 0)
        vm.reg.eflags_set(Reg32.CF, 0)

        a = to_int((vm.mem if type else vm.reg).get(loc, sz))
        b = to_int(vm.reg.get(R[1], sz))

        c = operation(a, b)

        vm.reg.eflags_set(Reg32.SF, (c >> (sz * 8 - 1)) & 1)

        c &= MAXVALS[sz]

        vm.reg.eflags_set(Reg32.ZF, c == 0)

        c = c.to_bytes(sz, byteorder)

        vm.reg.eflags_set(Reg32.PF, parity(c[0], sz))

        if not test:
            name = operation.__name__
            vm.reg.set(R[1], c)
        else:
            name = 'test'

        if debug: print('{0} r{1}({2}),{4}{1}({3})'.format(name, sz * 8, R[1], loc, ('m' if type else '_r')))

        return True


####################
# NEG / NOT
####################
class NEGNOT(Instruction):
    """
    NEG: two's complement negate
    Flags:
        CF flag set to 0 if the source operand is 0; otherwise it is set to 1.
        OF (!), SF, ZF, AF(!), and PF flags are set according to the result.

    NOT: one's complement negation  (reverses bits)
    Flags:
        None affected
    """

    def __init__(self):
        self.opcodes = {
            # NEG, NOT
            0xF6: [
                P(self.rm, _8bit=True, operation=0),
                P(self.rm, _8bit=True, operation=1)
                ],
            0xF7: [
                P(self.rm, _8bit=False, operation=0),
                P(self.rm, _8bit=False, operation=1)
                ]
            }

    @staticmethod
    def operation_not(a, off):
        return MAXVALS[off] - a

    @staticmethod
    def operation_neg(a, off):
        return NEGNOT.operation_not(a, off) + 1

    def rm(vm, _8bit, operation) -> bool:
        sz = 1 if _8bit else vm.operand_size
        old_eip = vm.eip

        RM, R = vm.process_ModRM(sz, sz)

        if operation == 0:  # NEG
            if R[1] != 3:
                vm.eip = old_eip
                return False  # this is not NEG
            operation = NEGNOT.operation_neg
        elif operation == 1:  # NOT
            if R[1] != 2:
                vm.eip = old_eip
                return False  # this is not NOT
            operation = NEGNOT.operation_not
        else:
            raise ValueError("Invalid argument to __negnot_rm: this is an error in the VM")

        type, loc, _ = RM

        a = to_int((vm.mem if type else vm.reg).get(loc, sz))
        if operation == NEGNOT.operation_neg:
            vm.reg.eflags_set(Reg32.CF, a != 0)

        b = operation(a, sz) & MAXVALS[sz]

        sign_b = (b >> (sz * 8 - 1)) & 1

        if operation == NEGNOT.operation_neg:
            vm.reg.eflags_set(Reg32.SF, sign_b)
            vm.reg.eflags_set(Reg32.ZF, b == 0)

        b = b.to_bytes(sz, byteorder)

        if operation == NEGNOT.operation_neg:
            vm.reg.eflags_set(Reg32.PF, parity(b[0], sz))

        vm.reg.set(loc, b)

        if debug: print('{0} {3}{1}({2})'.format(operation.__name__, sz * 8, loc, ('m' if type else '_r')))

        return True

####################
# SAL / SAR / SHL / SHR
####################
class SHIFT(Instruction):
    def __init__(self):
        self.opcodes = {
            # SHL, SHR, SAR
            0xD0: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_ONE, _8bit=True),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_ONE, _8bit=True),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_ONE, _8bit=True),
                ],
            0xD2: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_CL, _8bit=True),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_CL, _8bit=True),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_CL, _8bit=True),
                ],
            0xC0: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_imm8, _8bit=True),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_imm8, _8bit=True),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_imm8, _8bit=True),
                ],

            0xD1: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_ONE, _8bit=False),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_ONE, _8bit=False),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_ONE, _8bit=False),
                ],
            0xD3: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_CL, _8bit=False),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_CL, _8bit=False),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_CL, _8bit=False),
                ],
            0xC1: [
                P(self.shift, operation=Shift.SHL, cnt=Shift.C_imm8, _8bit=False),
                P(self.shift, operation=Shift.SHR, cnt=Shift.C_imm8, _8bit=False),
                P(self.shift, operation=Shift.SAR, cnt=Shift.C_imm8, _8bit=False)
                ]
            }

    def shift(self, operation, cnt, _8bit) -> True:
        sz = 1 if _8bit else self.operand_size
        old_eip = self.eip

        RM, R = self.process_ModRM(self.operand_size, self.operand_size)

        if (operation == Shift.SHL) and (R[1] != 4):
            self.eip = old_eip
            return False
        elif (operation == Shift.SHR) and (R[1] != 5):
            self.eip = old_eip
            return False
        elif (operation == Shift.SAR) and (R[1] != 7):
            self.eip = old_eip
            return False

        _cnt = cnt

        if cnt == Shift.C_ONE:
            cnt = 1
        elif cnt == Shift.C_CL:
            cnt = to_int(self.reg.get(1, 1))
        elif cnt == Shift.C_imm8:
            cnt = to_int(self.mem.get(self.eip, 1))
            self.eip += 1
        else:
            raise RuntimeError('Invalid count')

        tmp_cnt = cnt & 0x1F
        type, loc, _ = RM

        dst = to_int((self.mem if type else self.reg).get(loc, sz), signed=(operation==Shift.SAR))
        tmp_dst = dst

        if cnt == 0:
            return True

        while tmp_cnt:
            if operation == Shift.SHL:
                self.reg.eflags_set(Reg32.CF, (dst >> (sz * 8)) & 1)
                dst <<= 1
            else:
                self.reg.eflags_set(Reg32.CF, dst & 1)
                dst >>= 1

            tmp_cnt -= 1

        if cnt & 0x1F == 1:
            if operation == Shift.SHL:
                self.reg.eflags_set(Reg32.OF, ((dst >> (sz * 8)) & 1) ^ self.reg.eflags_get(Reg32.CF))
            elif operation == Shift.SAR:
                self.reg.eflags_set(Reg32.OF, 0)
            else:
                self.reg.eflags_set(Reg32.OF, (tmp_dst >> (sz * 8)) & 1)

        sign_dst = (dst >> (sz * 8 - 1)) & 1
        self.reg.eflags_set(Reg32.SF, sign_dst)

        dst &= MAXVALS[sz]

        self.reg.eflags_set(Reg32.ZF, dst == 0)

        dst = dst.to_bytes(sz, byteorder)

        self.reg.eflags_set(Reg32.PF, parity(dst[0], sz))

        (self.mem if type else self.reg).set(loc, dst)

        if operation == Shift.SHL:
            name = 'shl'
        elif operation == Shift.SHR:
            name = 'shr'
        elif operation == Shift.SAR:
            name = 'sar'

        if _cnt == Shift.C_ONE:
            op = ''
        elif _cnt == Shift.C_CL:
            op = ',cl'
        elif _cnt == Shift.C_imm8:
            op = ',imm8'

        if debug: print('{} {}{}{}'.format(name, 'm' if type else '_r', sz * 8, op))

        return True

