import array
import os

CPUBITS = 8
MEMLOC = 4096
STKSIZE = 100
PGMSTART = 0

# Memory addresses will be always aligned to 8 bits boundary
# The latest STKLOC locations are reserved for the stack
MEMSIZE = MEMLOC * CPUBITS
STKLOC = MEMLOC * CPUBITS
PGMAREA = PGMSTART * CPUBITS
mem0 = [0] * MEMSIZE
mem = array.array('b', mem0)
memoffset = 0

pmem = [""]

labels = [("", -1)]
vars = [("", "", -1)]
consts = [("", -1)]

lblnf = False
islabel = False
endf = False

pc = PGMAREA            # program counter
sp = STKLOC - CPUBITS  # stack pointer

bs = 0  # bus (16b)
mr = 0  # memory register
ir = 0  # instruction register

r0 = 0  # general purpose register 0
r1 = 0  # general purpose register 1
r2 = 0  # general purpose register 2
r3 = 0  # general purpose register 3
ac = 0  # accumulator (16b)
ev = 0  # excess value in arithmetic operation
fl = 0  # flags: [---UVZ] U=Underflow, V=Overflow, Z=Zero


def _dbg():
    global r0, r1, r2, r3, pc, ac, mem, fl
    print("R0:" + str(r0))
    print("R1:" + str(r1))
    print("R2:" + str(r2))
    print("R3:" + str(r3))
    print("PC:" + str(pc))
    print("AC:" + str(ac))
    print("EV:" + str(ev))
    print("FL:" + str(fl))
    yn = input("Print memory (Y/N)")
    if yn == "y" or yn == "Y":
        for x in range(0, MEMSIZE, CPUBITS):
            s = ""
            for y in range(x, x + CPUBITS):
                s = s + str(mem[y])
            print("MEM[0x{0:04x}]: {1:08b}".format(x, int(s, 2)))



def _npc():
    global pc
    pc = pc + CPUBITS


def _nsp():
    global sp
    sp = sp - CPUBITS
    if sp < STKLOC - STKSIZE:
        print("Warning: Stack too big... can be overwritten!")


def _psp():
    global sp
    sp = sp + CPUBITS


def lblfind(l):
    global labels
    global lblnf
    l = l.strip()
    for ll in labels:
        if l == ll[0]:
            return int(ll[1])
    lblnf = True
    return -1


def lblput(l):
    global labels
    if lblfind(l[0]) == -1:
        labels.append(l)


def _fixaddr(v):
    (d1, d2) = divmod(v, CPUBITS)
    if d2 != 0:
        v = (d1 * CPUBITS) + (CPUBITS * d2)
    return v


def _fixval(v):
    if v < 0:
        return ((1 << CPUBITS) - 1) & v
    elif v > 255:
        return v & 0xff
    return v


def _fixval16(v):
    if v < 0:
        return ((1 << (2*CPUBITS)) - 1) & v
    elif v > 65535:
        return v & 0xffff
    return v


def _isint(v):
    try:
        vv = int(v)
    except ValueError:
        return False
    return True


def _memwrite(loc, val):
    global mem
    val = _fixval(val)
    valb = f'{val:08b}'
    loc = _fixaddr(loc)
    for b in valb:
        mem[loc] = int(b)
        loc = loc + 1
    pass


def _memread(loc):
    global mem
    ls = ""
    loc = _fixaddr(loc)
    for x in range(CPUBITS):
        ls = ls + str(mem[loc + x])
    return int(ls, 2)
    pass


def _push(v):
    global sp
    _memwrite(sp, v)
    _nsp()


def _pop():
    global sp
    _psp()
    v = _memread(sp)
    return v


def _regwrite(r):
    global mem, sp, r0, r1, r2, r3
    valh =0
    vall = _pop()
    if r == 0:
        valh = _pop()
        r0 = (valh << 8) + vall
    elif r == 1:
        valh = _pop()
        r1 = (valh << 8) + vall
    elif r == 2:
        r2 = vall
    elif r == 3:
        r3 = vall
    else:
        pass


def _arg(f):
    global c, endf
    c = f.read(1)
    a = ""
    while (c != '#' and c != '$' and c != '!' and c != '\\'
           and c != '@' and c != '[' and c != '{'
           and c != '<' and c != ">"):
        if not c:
            break
        a = a + c
        c = f.read(1)
    if _isint(a):
        return int(a)
    else:
        return a


def cmp(t):
    global ev, r0, r1, r2, r3
    if t == 12:
        if r0 == r1:
            ev = 0
        elif r0 > r1:
            ev = 1
        else:
            ev = 2
    elif t == 48:
        if r2 == r3:
            ev = 0
        elif r2 > r3:
            ev = 1
        else:
            ev = 2


def _load(fn):
    global endf
    f = open(fn, 'r')
    nbytes = 0
    while True:
        c = f.read(1)
        ah = 0
        al = 0
        if (not c) or endf:
            break
        elif c == '\n' or c == ' ':
            pass
        elif c == '#':
            a = _arg(f)
            _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            _npc()
            _memwrite(pc, a)
            nbytes = nbytes + CPUBITS
            _npc()
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '@':
            a = _arg(f)
            if a == 'E':
                _memwrite(pc, ord(c)+9)
            else:
                _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            _npc()
            ah = int(a) >> 8
            _memwrite(pc, ah)
            nbytes = nbytes + CPUBITS
            _npc()
            al = int(a) & 0xff
            _memwrite(pc, al)
            nbytes = nbytes + CPUBITS
            _npc()
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '!':
            a = _arg(f)
            if _isint(a):
                a = a
            else:
                a = a.strip()
            if _isint(a):
                _memwrite(pc, ord(c))
                nbytes = nbytes + CPUBITS
                _npc()
                _memwrite(pc, a)
                nbytes = nbytes + CPUBITS
                _npc()
            elif a[0] == 'j' or a[0] == 'l' or a[0] == 'g' or a[0] == 'z' or a[0] == 'n':
                _memwrite(pc, ord(a[0]))
                nbytes = nbytes + CPUBITS
                _npc()
                if _isint(a[1:]):
                    _memwrite(pc, PGMAREA + int(a[1:]))
                else:
                    _memwrite(pc, PGMAREA + lblfind(a[1:]))
                # nbytes = nbytes + CPUBITS
                _npc()
            elif a == '+':
                _memwrite(pc, ord(a))
                nbytes = nbytes + CPUBITS
                _npc()
            elif a[0] == 'C':
                if a[1:] == "01":
                    _memwrite(pc, ord(a[0]) + 12)
                else:
                    _memwrite(pc, ord(a[0]) + 48)
                nbytes = nbytes + CPUBITS
                _npc()
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '$':
            a = _arg(f)
            _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            _npc()
            lblput((a, nbytes))
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '+':
            _memwrite(pc, ord(c))
            _npc()
        elif c == '>':
            a = _arg(f)
            a = a << 6
            _memwrite(pc, ord(c) + a)
            nbytes = nbytes + CPUBITS
            _npc()
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '<':
            a = _arg(f)
            a = a << 6
            _memwrite(pc, ord(c) + a)
            nbytes = nbytes + CPUBITS
            _npc()
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '\\':
            _memwrite(pc, ord(c))
            endf = True
        else:
            pass
    f.close()


def _exec():
    global pc, r0, r1, r2, r3, ac, ev
    pc = PGMAREA
    endr = False

    while not endr:
        c = _memread(pc)
        a = 0
        ah = 0
        al = 0
        if c == ord('\\'):
            endr = True
        if c == ord('#'):
            _npc()
            a = _memread(pc)
            _push(a)
            _npc()
        if c == ord('@') or c == ord('@')+9:
            if (c & 0xf) == 9:
                _push(ev)
                _npc()
            else:
                _npc()
                ah = _memread(pc)
                _push(ah)
                _npc()
                al = _memread(pc)
                _push(al)
                _npc()
        elif c == ord('!'):
            _npc()
            a = _memread(pc)
            _regwrite(a)
            _npc()
        elif c == ord('$'):
            _npc()
        elif c == ord('+'):
            ac = ac + r0 + r1
            _npc()
        elif c == ord('-'):
            ac = ac - r0 + r1
            _npc()
        elif c == ord('*'):
            ac = ac * (r0 + r1)
            _npc()
        elif c == ord('/'):
            ac, ev = divmod(ac, (r0 + r1))
            _npc()
        elif c == ord('j'):
            _npc()
            pc = _memread(pc)
        elif c == ord('l'):
            _npc()
            if ev == 2:
                pc = _memread(pc)
            else:
                _npc()
        elif (c == ord('C') + 12) or (c == ord('C') + 48):
            cmp(c & 0x3c)
            _npc()
        elif c == ord('<') or (c == ord('<') + 64) or (c == ord('<') + 128) or (c == ord('<') + 192):
            if (c & 0xC0) == 0:
                r0 = r0 - 1
            elif (c & 0xC0) == 1:
                r1 = r1 - 1
            elif (c & 0xC0) == 2:
                r2 = r2 - 1
            elif (c & 0xC0) == 3:
                r3 = r3 - 1
            _npc()
        elif c == ord('>') or (c == ord('>') + 64) or (c == ord('>') + 128) or (c == ord('>') + 192):
            if (c & 0xC0) >> 6 == 0:
                r0 = r0 + 1
            elif (c & 0xC0) >> 6 == 1:
                r1 = r1 + 1
            elif (c & 0xC0) >> 6 == 2:
                r2 = r2 + 1
            elif (c & 0xC0) >> 6 == 3:
                r3 = r3 + 1
            _npc()
        else:
            pass


if __name__ == '__main__':
    _load("test1.mem")
    _exec()
    _dbg()
