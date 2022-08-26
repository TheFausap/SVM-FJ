import array
import os
from io import StringIO

CPUBITS = 8
MEMLOC = 8192
STKSIZE = 256
VARSIZE = 1024
EVSIZE = 1024
PGMSTART = 0

# Memory addresses will be always aligned to 8 bits boundary
# The latest STKLOC locations are reserved for the stack
MEMSIZE = MEMLOC * CPUBITS
STKLOC = MEMLOC * CPUBITS
PGMAREA = PGMSTART * CPUBITS
VARAREA = (MEMLOC - STKSIZE - VARSIZE) * CPUBITS
EVAREA = (MEMLOC - STKSIZE - VARSIZE - EVSIZE) * CPUBITS
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

pc = PGMAREA  # program counter
sp = STKLOC - CPUBITS  # stack pointer
vp = VARAREA  # variable/macro area
ep = EVAREA  # extended EV area for big integer numbers

bs = 0  # bus (16b)
mr = 0  # memory register
ir = 0  # instruction register

r0 = 0  # general purpose register 0
r1 = 0  # general purpose register 1
r2 = 0  # general purpose register 2
r3 = 0  # general purpose register 3
ac = 0  # accumulator (16b)
ev = 0  # excess value in arithmetic operation
carry = 0  # carry value. Sometimes is also ev
fl = 0  # flags: [--EUVZ] E=Excess overflow, U=Underflow, V=Overflow, Z=Zero


def _pm(s, e):
    for x in range(s, e, CPUBITS):
        s = ""
        for y in range(x, x + CPUBITS):
            s = s + str(mem[y])
        print("MEM[0x{0:04x}]: {1:08b}".format(x, int(s, 2)))


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
    yn = input("Print entire memory? (Y/N)")
    if yn == "y" or yn == "Y":
        _pm(0, MEMSIZE)
    yn = input("Print VARAREA memory? (Y/N)")
    if yn == "y" or yn == "Y":
        _pm(VARAREA, VARAREA + VARSIZE)
    yn = input("Print EVAREA memory? (Y/N)")
    if yn == "y" or yn == "Y":
        _pm(EVAREA, EVAREA + EVSIZE)


def _npc(pc):
    return pc + CPUBITS


def _nsp():
    global sp
    sp = sp - CPUBITS
    if sp < STKLOC - (STKSIZE * CPUBITS):
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
        return v + (1 << CPUBITS)
    elif v > pow(2, CPUBITS) - 1:
        return v & (pow(2, CPUBITS) - 1)
    return v


def _fixval16(v):
    if v < 0:
        return v + (1 << (2 * CPUBITS))
    elif v > pow(2, (2 * CPUBITS)) - 1:
        return v & (pow(2, (2 * CPUBITS)) - 1)
    return v


def _chkresult():
    global fl, ac, ev, carry, vp, ep
    if ac > (pow(2, (2 * CPUBITS)) - 1):
        ev = ac >> 2 * CPUBITS
        if ev > (pow(2, (2 * CPUBITS)) - 1):
            _memwrite16(ep, ev >> (2 * CPUBITS))
            ep = ep + (2 * CPUBITS)
            _memwrite16(ep, ev & (pow(2, (2 * CPUBITS)) - 1))
            ep = ep + (2 * CPUBITS)
            ev = 0
            fl = fl | 0x8
        ac = ac & (pow(2, (2 * CPUBITS)) - 1)
        fl = fl | 0x2
        carry = 1
    elif ac < 0:
        ac = ac + (1 << (2 * CPUBITS))
        ev = 1
        carry = 1
        fl = fl | 0x4
    elif ac == 0 and ev == 0 and carry == 0:
        fl = fl | 0x1


def _popev():
    global ep
    ep = ep - (2 * CPUBITS)
    evl = _memread16(ep)
    ep = ep - (2 * CPUBITS)
    evh = _memread16(ep)
    return (evh << 16) + evl


def _isint(v):
    try:
        vv = int(v)
    except ValueError:
        return False
    return True


def _memwrite(loc, val):
    global mem
    val = _fixval(val)
    valsz = '0' + str(CPUBITS) + 'b'
    valb = f'{val:{valsz}}'
    loc = _fixaddr(loc)
    for b in valb:
        mem[loc] = int(b)
        loc = loc + 1
    pass


def _memwrite16(loc, val):
    global mem
    val = _fixval(val)
    valb = f'{val:016b}'
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


def _memread16(loc):
    global mem
    ls = ""
    loc = _fixaddr(loc)
    for x in range(16):
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


def _push16(v):
    global sp
    vh = v >> 8
    vl = v & 0xff
    _memwrite(sp, vh)
    _nsp()
    _memwrite(sp, vl)
    _nsp()


def _pop16():
    global sp
    _psp()
    _psp()
    v = _memread16(sp)
    return v


def _regwrite(r):
    global mem, sp, r0, r1, r2, r3
    valh = 0
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
           and c != '<' and c != ">" and c != "`"):
        if not c:
            break
        a = a + c
        c = f.read(1)
    if _isint(a):
        return int(a)
    else:
        return a.strip()


def body(f):
    global c, endf
    c = f.read(1)
    a = ""
    while (c != ']'):
        a = a + c
        c = f.read(1)
    return a.strip().split(':')


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


def _load(f, count):
    global vp

    pc = count
    endf = False
    nbytes = 0
    while True:
        c = f.read(1)
        ah = 0
        al = 0
        if (not c) or endf:
            break
        elif c == '\\':
            _memwrite(pc, ord(c))
            endf = True
        elif c == '\n' or c == ' ':
            pass
        elif c == '#':
            a = _arg(f)
            _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            _memwrite(pc, a)
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '@':
            a = _arg(f)
            if a == 'E':
                _memwrite(pc, ord(c) + 9)
                nbytes = nbytes + CPUBITS
            elif a == 'A':
                _memwrite(pc, ord(c) + ord('A'))
                nbytes = nbytes + CPUBITS
            else:
                _memwrite(pc, ord(c))
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
                ah = int(a) >> 8
                _memwrite(pc, ah)
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
                al = int(a) & 0xff
                _memwrite(pc, al)
                nbytes = nbytes + CPUBITS
            pc = _npc(pc)
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
                pc = _npc(pc)
                _memwrite(pc, a)
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
            elif a[0] == 'j' or a[0] == 'l' or a[0] == 'g' or a[0] == 'z' or a[0] == 'n':
                _memwrite(pc, ord(a[0]))
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
                if _isint(a[1:]):
                    _memwrite(pc, PGMAREA + int(a[1:]))
                else:
                    _memwrite(pc, PGMAREA + lblfind(a[1:]))
                # nbytes = nbytes + CPUBITS
                pc = _npc(pc)
            elif a == '+' or a == '-' or a == '*' or a == '/' or a == '^':
                _memwrite(pc, ord(a))
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
            elif a[0] == 'C':
                if a[1:] == "01":
                    _memwrite(pc, ord(a[0]) + 12)
                else:
                    _memwrite(pc, ord(a[0]) + 48)
                nbytes = nbytes + CPUBITS
                pc = _npc(pc)
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '$':
            a = _arg(f)
            _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            lblput((a, nbytes))
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '>':
            a = _arg(f)
            a = a << 6
            _memwrite(pc, ord(c) + a)
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '<':
            a = _arg(f)
            a = a << 6
            _memwrite(pc, ord(c) + a)
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '[':
            nb = 0
            nvp = 0
            a = body(f)  # a[0] = label, a[1] = body
            lblput((a[0], vp))
            nb = _load(StringIO(a[1]), vp)
            vp = vp + nb - CPUBITS
            f.seek(f.tell() - 1, os.SEEK_SET)
        elif c == '`':
            a = _arg(f)
            _memwrite(pc, ord(c))
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            ah = lblfind(a) >> 8
            al = lblfind(a) & 0xff
            _memwrite(pc, al)
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            _memwrite(pc, ah)
            nbytes = nbytes + CPUBITS
            pc = _npc(pc)
            f.seek(f.tell() - 1, os.SEEK_SET)
        else:
            pass
    return nbytes
    f.close()


def _exec(pc, macro):
    global r0, r1, r2, r3, ac, ev
    endr = False

    while not endr:
        c = _memread(pc)
        a = 0
        ah = 0
        al = 0
        if c == ord('\\'):
            if not macro:
                endr = True
            else:
                return
        if c == ord('#'):
            pc = _npc(pc)
            a = _memread(pc)
            _push(a)
            pc = _npc(pc)
        if c == ord('@') or c == ord('@') + 9 or c == ord('@') + ord('A'):
            if (c & 0xf) == 9:
                _push16(ev)
                pc = _npc(pc)
            elif (c & 0x1) == 1:
                _push16(ac)
                pc = _npc(pc)
            else:
                pc = _npc(pc)
                ah = _memread(pc)
                _push(ah)
                pc = _npc(pc)
                al = _memread(pc)
                _push(al)
                pc = _npc(pc)
        elif c == ord('!'):
            pc = _npc(pc)
            a = _memread(pc)
            _regwrite(a)
            pc = _npc(pc)
        elif c == ord('$'):
            pc = _npc(pc)
        elif c == ord('+'):
            if (fl & 0x8) == 0:
                ac = ((ev << (2*CPUBITS)) + ac) + r0 + r1
            else:
                ev = _popev()
                ac = (ac + ev) + r0 + r1
            _chkresult()
            pc = _npc(pc)
        elif c == ord('-'):
            ac = ((ev << (2*CPUBITS)) + ac) - (r0 + r1)
            _chkresult()
            pc = _npc(pc)
        elif c == ord('*'):
            ac = ((ev << (2*CPUBITS)) + ac) * (r0 + r1)
            _chkresult()
            pc = _npc(pc)
        elif c == ord('^'):
            ac = (((ev << (2*CPUBITS)) + ac) * r0) * r1
            _chkresult()
            pc = _npc(pc)
        elif c == ord('/'):
            ac, r1 = divmod(((ev << (2*CPUBITS)) + ac), (r0 + r1))
            _chkresult()
            pc = _npc(pc)
        elif c == ord('j'):
            pc = _npc(pc)
            pc = _memread(pc)
        elif c == ord('l'):
            pc = _npc(pc)
            if ev == 2:
                pc = _memread(pc)
            else:
                pc = _npc(pc)
        elif (c == ord('C') + 12) or (c == ord('C') + 48):
            cmp(c & 0x3c)
            pc = _npc(pc)
        elif c == ord('<') or (c == ord('<') + 64) or (c == ord('<') + 128) or (c == ord('<') + 192):
            if (c & 0xC0) == 0:
                r0 = r0 - 1
            elif (c & 0xC0) == 1:
                r1 = r1 - 1
            elif (c & 0xC0) == 2:
                r2 = r2 - 1
            elif (c & 0xC0) == 3:
                r3 = r3 - 1
            pc = _npc(pc)
        elif c == ord('>') or (c == ord('>') + 64) or (c == ord('>') + 128) or (c == ord('>') + 192):
            if (c & 0xC0) >> 6 == 0:
                r0 = r0 + 1
            elif (c & 0xC0) >> 6 == 1:
                r1 = r1 + 1
            elif (c & 0xC0) >> 6 == 2:
                r2 = r2 + 1
            elif (c & 0xC0) >> 6 == 3:
                r3 = r3 + 1
            pc = _npc(pc)
        elif c == ord("`"):
            pc = _npc(pc)
            al = _memread(pc)
            pc = _npc(pc)
            ah = _memread(pc)
            a = (ah << 8) + al
            _exec(a, True)
            pc = _npc(pc)
        else:
            pass


if __name__ == '__main__':
    f = open("test3.mem", 'r')
    _load(f, PGMAREA)
    _exec(PGMAREA, False)
    _dbg()
