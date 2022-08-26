## STACK CPU

### GENERAL INFORMATION

- CPUBITS = 8
- MEMLOC = number of memory locations : 8192
- STKSIZE = number of locations: 256
- VARSIZE = area where macro are stored: 1024 loc
- EVSIZE = area where overflow ev is stored: 1024 loc
- PGMSTART = programs always start at 0 memory

| NAME    | AREA            | SIZE |
|---------|-----------------|------|
| MEMSIZE | 0x0000 - 0xFFFF | 64KB |
| STACK   | 0xFFFF - 0xF7FF | 2KB  |
| MACROS  | 0xD800 - 0xDBFF | 8KB  |
| EVAREA  | 0xD800 - 0xDBFF | 8KB  |

Memory addresses will be always aligned to 8 bits boundary
The latest STKSIZE locations in memory are reserved for the stack.
After the stack, 1024 locations are for macros.

### CPU Registries

- R0 : general purpose register 0 (16 bits)
- R1 : general purpose register 1 (16 bits)
- R2 : general purpose register 2 (8 bits)
- R3 : general purpose register 3 (8 bits)
- AC : accumulator (16 bits)
- EV : excess value in arithmetic operation (16 bits)
- FL : flags: [--EUVZ] E=Excess overflow, U=Underflow, V=Overflow, Z=Zero. Flag V is also a carry.

### Machine language

It's in a sort of tape format, FORTH-like.
The operators are case-sensitive.

- '#' : the following 8-bit number is pushed to the stack
- '@' : the following 16-bit number is pushed to the stack. @E is a
  special form, pushing EV content into the stack. @A is a special form
  to push the AC to the stack
- '!0', '!1', etc : the value popped from the stack is stored in R0, R1, etc
- '!+' : the sum of R0 and R1 are added to AC. AC get the new value.
  If AC > 65535, EV will contain the excess and 'V' flag will be set. If EV > 65535 'E' flag will be set
- '!-' : AC is subtracted from the sum of R0 and R1. AC get the new value.
  If AC < 0, EV will contain the sign and the excess and 'U' flag will be set. If EV > 65535 'E' flag will be set
- '!*' : the sum of R0 and R1 are multiplied by AC. AC get the new value.
  If AC > 65535, EV will contain the excess and 'V' flag will be set. If EV > 65535 'E' flag will be set
- '!^' : AC is multiplied by R0 and the result is multiplied by R1. AC get the new value.
  If AC > 65535, EV will contain the excess and 'V' flag will be set. If EV > 65535 'E' flag will be set
- '!/' : AC is divided by the sum of R0 and R1. AC get the new value. R1 will contain the remainder.
- '$' : set a label, used for a jump instruction,
- '!j' : unconditional jump,
- '!C01' ('!C23') : compare instruction between R0 and R1 (R2 and R3).

The following table will be used:

| COND    | EV  | Note                       |
|---------|-----|----------------------------|
| RX > RY | 1   | (X=0, Y=1) or (X=2, Y=3)   |
| RX < RY | 2   | (X=0, Y=1) or (X=2, Y=3)   |
| RX = RY | 0   | (X=0, Y=1) or (X=2, Y=3)   |

- '!g': conditional jump if ev = 1
- '!l': conditional jump if ev = 2
- '!z': conditional jump if ev = 0
- '!n': conditional jump if ev != 0
- '>': increment by 1 the register pointed by that following number.
  It can generate overflow and set the flag (V)
- '<': decrement by 1 the register pointed by that following number.
  It can generate zero or underflow and set the
  flags (Z or U)
- '[]': macro
- '`': calls a macro
- '\\': end a program or a macro. If it used in a macro, it behaves
  like a a jump back to the original memory location
- '~': clear operator. It uses the following table as second letter

| Letter| Operates on |
|-------|-------------|
| A     | AC          |
| E     | EV          |
| V     | Flag V      |
| Z     | Flag Z      |
| U     | Flag U      |

### Macros

The terms '[]' or '{}' introduce macros.
The structure of a macro is the following:

[name:content]

Macros are introduced to save space in the coding and in the memory.
They have no arguments and they do not return any value.

### Integer arithmetic

The ac, the registers r0 and r1 are treated as 16bit wide in the VM memory
(internally they are arbitrary wide) so the integer arithmetic (unsigned) can store value
between 0 and 65535 without overflow. If the overflow occurs,
other 16bit are available to calculate the remaining digits.
The registry used is EV. If EV overflows, there is a dedicated EVAREA
(1024bits) to store the ev digits.