# PyVM - execute x86 bytecode in pure Python!

PyVM is a Python module that allows to execute x86 32-bit (IA-32) bytecode on any hardware where Python can run, with no external dependencies.

The instructions' opcodes as well as their operation algorithms have been taken from the [Intel Software Development Manual](https://software.intel.com/en-us/articles/intel-sdm).

## Features

* 32-, 16- and 8-bit registers
* stack
* user memory
* stdin, stdout and stderr

## Instructions currently supported

The instructions  marked wth `*` are supported partially. For the actual reasons of this partial support, please see the `#TODO` comments in `VM/instructions/<category>.py`.

1.  `adc`
2.  `add`
3.  `and`
4.  `call` (*)
5.  `cdq`
5.  `clc`
6.  `cld`
7.  `cli`
8.  `cmc`
5.  `cmp`
6.  `cwd`
7.  `cwde`
6.  `dec`
7.  `div`
8.  `idiv`
9.  `imul`
9.  `inc`
10. `int`
7.  `jcc`  (*)
8.  `jmp`  (*)
11. `lea`
12. `leave`
13. `mov`  (*)
14. `movsb`
15. `movsx`
16. `movsxd`
15. `movsw`
16. `movzx`
16. `mul`
14. `neg`  (*)
15. `nop`
15. `not`  (*)
16. `or`
17. `pop`
18. `push`
19. `ret`  (*)
20. `sal`
21. `sar`
22. `sbb`
23. `shl`
24. `shr`
25. `stc`
26. `std`
27. `sti`
25. `sub`
26. `test`
27. `xchg`
27. `xor`

## Documentation

### Memory

If you would like to manipulate the memory directly, look into `VM/Memory.py`, which defines a class `Memory` that is later used in `VM/CPU.py` to handle all memory operations of the `CPU` class. It checks whether the bounds of the available memory aren't exceed automatically. The memory is zero-filled by default.

There are two functions that allow the VM to manipulate data stored in memory:

* `Memory.set(self, offset: int, value: bytes) -> None` - set the memory region starting at address `offset` to the given `value`. Again, here and thereon, that the value can actually be written or read is checked automatically, and if it cannot, an exception is raised.
* `Memory.get(self, offset: int, size: int) -> bytes` - read `size` bytes from memory starting at address `offset`.
* `Memory.fill(self, offset: int, value: int) -> None` - fill the memory starting at address `offset` with a byte with the given `value`.

### Registers

The `Reg32` class defined in `VM/Registers.py` handles all operations with registers: general-purpose ones and EFLAGS. Segment registers support is yet to be implemented.

There are two functions that govern the access to individual registers. Note that their signatures are absolutely the same as those of `Memory.Memory`:

* `Reg32.set(self, offset: int, value: bytes) -> None` - set a register with the number `offset` (the registers' numbers are given in the Intel Software Development Manual (see 2.1.5, tables 2-1 and 2-2; the register number is the value of REG given in the 7th row) to the given `value`. The size of the value determines the size of the register to use.
* `Reg32.get(self, offset: int, size: int) -> bytes` - read `size` bytes of the register number `offset`.
* `Reg32.eflags_set(self, bit: int, value: bool) -> None` - set the EFLAGS bit number `bit` to the given `value` (`True` or `False`).
* `Reg32.eflags_get(self, bit: int) -> int` - get the value of the EFLAGS bit number `bit`.

### CPU

The `CPU32` class is defined in `VM/CPU.py`. It sets up the memory (represented by `VM.Memory.Memory`) and registers (represented by `VM.Registers.Reg32`) and gives the ability to work with the stack.

* `CPU32.stack_push(self, value: bytes) -> None` - push a `value` onto stack. The memory bounds are checked automatically, as in the following function.
* `CPU32.stack_pop(self, size: int) -> bytes` - pop `size` bytes from the stack.

### VM

The `VM` class is defined in `VM.__init__.py`. It inherits from `VM.CPU.CPU32` and provides a lot of additional functions, the majority of which need not to be accessed directly by the user code. This is the class that actually runs the binary.

There are only 3 user-level functions:

* `VM(memory_size: int)` - the constructor, accepts a positive integer that determines the amount of memory to be allocated for the VM, in bytes.
* `execute_bytes(data: bytes, offset=0)` - load the given data into memory starting from address `offset` and execute it.
* `execute_file(file_name: str, offset=0)` - load the contents of the given file into memory starting from address `offset` and execute it.

The individual instructions are implemented as classes in `VM/instructions/<category>.py`.


## Example

Before running this you may consider setting `debug = False` in `VM/debug.py`, if it's not already set.

	import VM

	code = """
	B8 04 00 00 00
    BB 01 00 00 00
    B9 29 00 00 00
    BA 0E 00 00 00
    CD 80
    E9 02 00 00 00
    89 C8
    B8 01 00 00 00
    BB 00 00 00 00
    CD 80
    48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 21 0A
    """

    # convert the hexadecimal representation above to bytes
    binary = bytearray.fromhex(code.strip('\n').replace('\n', ' '))

    # initialize the VM with 128 bytes of memory
    vm = VM.VM(128)

    vm.execute_bytes(binary)

    # output:
    # Hello, world!
    # [!] Process exited with code 0

## TODO

* Add segment registers
* Implement more instructions
* Add basic memory protection

## How to deal with errors

If you decide to open an issue, please include a minimal, complete and verifiable example that reproduces the error and the traceback.

* Not enough memory supplied -> increase the amount of memory given to the VM

      Traceback (most recent call last):
        File "...", line 53, in <module>
          vm.execute_bytes(binary)
        File ".../VM/fetchLoop.py", line ..., in execute_bytes
          self.mem.set(offset, data)
        File ".../VM/Memory.py", line ..., in set
          assert offset + size in self.bounds
      AssertionError

* Unknown opcode -> please open an issue entitled `Unknown opcode: [opcode in hex]`

      ...
      ValueError: Unknown opcode: 0xf8

* The executable attempted to access a nonexistent memory location -> make sure your code _absolutely cannot_ do this (that is, works fine after having been assembled, linked and run as a native executable), that there's enough memory supplied to the VM and open an issue entitled `Invalid memory access`.

      ...
         assert offset + size in self.bounds
      AssertionError

* Other errors -> please open an issue entitled accordingly

## How to contribute

Everyone is welcome to contribute! For some guidelines, please refer to the comments in the project, especially in `VM/__init__.py`, `VM/fetchLoop.py` and `VM/instructions`.
