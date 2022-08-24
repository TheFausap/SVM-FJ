## STACK CPU

### GENERAL INFORMATION

- CPUBITS = 8
- MEMLOC = number of memory locations : 8192
- STKSIZE = number of locations: 256
- VARSIZE = area where macro are stored: 1024 loc
- PGMSTART = programs always start at 0 memory

| NAME    | AREA            | SIZE |
|---------|-----------------|------|
| MEMSIZE | 0x0000 - 0xFFFF | 64KB |
| STACK   | 0xFFFF - 0xF7FF | 2KB  |
| MACROS  | 0xD800 - 0xDBFF | 8KB  |

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
- FL : flags: [---UVZ] U=Underflow, V=Overflow, Z=Zero


### Machine language

It's in a sort of tape format, FORTH-like.
The operators are case-sensitive.

- '#' : the following 8-bit number  is pushed to the stack
- '@' : the following 16-bit number is pushed to the stack. @E is a special form, pushing EV content into the stack
- '!0', '!1', etc : the value popped from the stack is stored in R0, R1, etc
- '!+' : the sum of R0 and R1 are added to AC. AC get the new value. If AC > 65535, EV will contain the excess and 'V' flag will be set
- '$' : set a label, used for a jump instruction
- '!j' : unconditional jump
- '!C01' ('!C23') : compare instruction between R0 and R1 (R2 and R3). The following table will be used: 

| COND    | EV  | Note                       |
|---------|-----|----------------------------|
| RX > RY | 1   | (X=0, Y=1) or (X=2, Y=3)   |
| RX < RY | 2   | (X=0, Y=1) or (X=2, Y=3)   |
| RX = RY | 0   | (X=0, Y=1) or (X=2, Y=3)   |

- '!g': conditional jump if ev = 1
- '!l': conditional jump if ev = 2
- '!z': conditional jump if ev = 0
- '!n': conditional jump if ev != 0
- '>': increment by 1 the register pointed by that following number. It can generate overflow and set the flag (V)
- '<': decrement by 1 the register pointed by that following number. It can generate zero or underflow and set the
  flags (Z or U)
- '{}': macro with expansion (nested macro, not yet implemented)
- '[]': macro without expansion (no nested macro)
- '`': calls a macro
- '\\': end a program or a macro. If it used in a macro, it behaves like a a jump back to the original mem location


### Macros

The terms '[]' or '{}' introduce macros.
The structure of a macro is the following:

[Lname*:content]

{Lname*:content}

The name part is optional, if present it's a named macro (like a function).
The args part is also optional.