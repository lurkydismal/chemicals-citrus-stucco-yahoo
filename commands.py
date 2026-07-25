from __future__ import annotations

from pathlib import Path
import lldb

"""
===============================================================================
LLDB helper commands for debugging X-Ray Engine minidumps
===============================================================================

This script adds a collection of commands intended to speed up debugging
STALKER Anomaly/X-Ray Engine crashes.

Typical workflow
----------------

1. Open the newest crash dump.

    (lldb) latest-mdmp

This searches DUMP_DIR for the newest *.mdmp and executes

    target create --core <dump> <exe>

2. Load symbols.

    (lldb) load-symbols

This loads the project's PDB so LLDB can resolve source locations,
function names, variables and types.

3. Get a quick overview of the crash.

    (lldb) crash

Output:
    • selects thread 1
    • selects frame 0 (faulting frame)
    • prints the backtrace
    • prints frame information
    • prints CPU registers

Example:

    CInventoryOwner::load(...)
    InventoryOwner.cpp:205

At this point you know exactly where execution stopped.

4. Determine why it crashed.

    (lldb) why

Output:
    • function arguments
    • local variables
    • disassembly of the current function

Typical things to look for:

    • nullptr dereference
    • invalid "this" pointer
    • invalid function arguments
    • corrupted stack values
    • crashing instruction

5. Inspect the current object.

    (lldb) this

Shows

    this
    *this

Useful inside member functions to inspect the current object's state.

6. Show only function arguments.

    (lldb) args

Useful when you only care about inputs.

7. Show only local variables.

    (lldb) locals

Useful after stepping into a function.

8. Navigate the call stack.

Current frame:

    frame #0

Move to the caller:

    (lldb) upn

Move several frames:

    (lldb) upn 3

Move back toward the crash:

    (lldb) downn

or

    (lldb) downn 2

Each command automatically prints information about the selected frame.

9. View the surrounding source.

    (lldb) source

Shows approximately twenty lines around the current location.

10. View generated assembly.

    (lldb) asm

Shows approximately thirty instructions around the current PC.

Useful when:

    • compiler optimizations changed the code
    • source and assembly disagree
    • debugging optimized builds

11. Show only the crashing instruction.

    (lldb) pc

Useful when identifying the exact instruction that faulted.

Typical output:

    mov eax, [rcx+0x20]

Combined with register values you can immediately determine whether RCX
(or another register) contains an invalid pointer.

12. Inspect the virtual table pointer.

    (lldb) vptr

Shows

    *(void**)this

Useful for detecting

    • use-after-free
    • object corruption
    • wrong dynamic type

13. Quick object sanity check.

    (lldb) sus

Displays

    • this pointer
    • *this
    • CPU registers
    • nearby assembly

Useful when an object "looks wrong" and you want a quick overview.

14. Spawn-related debugging.

    (lldb) spawn

Designed for crashes during

    net_Spawn()
    net_Load()
    g_sv_Spawn()
    cl_Process_Spawn()

The command prints

    • backtrace
    • caller frame
    • current object

This makes it easy to inspect the object immediately before or after
spawning.

===============================================================================

Example session
---------------

(lldb) latest-mdmp

(lldb) load-symbols

(lldb) crash

frame #0:
CInventoryOwner::load()

(lldb) why

-> inventory = 0x0
-> this = 0x000001D29A123450

(lldb) this

Inspect the object's fields.

(lldb) upn

Move to

CAI_Stalker::load()

(lldb) locals

Inspect local variables.

(lldb) source

Open the surrounding source code.

(lldb) asm

Inspect the generated instructions.

(lldb) pc

Verify the exact instruction that faulted.

(lldb) vptr

Ensure the object's vtable pointer is valid.

If the crash occurred during spawning:

(lldb) spawn

===============================================================================

Recommended investigation order

    latest-mdmp
    load-symbols
    crash
    why
    this
    upn / downn
    source
    asm
    pc
    vptr
    sus

Following this order usually identifies the failing object, the failing
instruction, and the root cause in only a few commands.

===============================================================================
"""

EXE = Path(
    "/mnt/hdd/SG094/STALKER_GAMMA (1)/STALKER_GAMMA/game_info/data/Anomaly/bin/AnomalyDX11.exe"
)
DUMP_DIR = Path(
    "/mnt/hdd/SG094/STALKER_GAMMA (1)/STALKER_GAMMA/game_info/data/Anomaly/appdata/logs"
)
PDB = Path(
    "/mnt/hdd/SG094/STALKER_GAMMA (1)/STALKER_GAMMA/game_info/data/Anomaly/bin/AnomalyDX11.pdb"
)


def latest_mdmp(
    debugger: lldb.SBDebugger,
    command: str,
    result: lldb.SBCommandReturnObject,
    internal_dict: dict[str, object],
) -> None:
    """
    Load the most recently created minidump.

    Finds the newest *.mdmp file in DUMP_DIR and executes:

        target create --core <dump> <exe>

    This is typically the first command to run after a crash.

    Example:
        (lldb) latest-mdmp
    """
    dumps = list(DUMP_DIR.glob("*.mdmp"))
    if not dumps:
        result.SetError("No .mdmp files found")
        return

    latest = max(dumps, key=lambda p: p.stat().st_mtime)

    debugger.HandleCommand(f'target create --core "{latest}" "{EXE}"')


def load_symbols(
    debugger: lldb.SBDebugger,
    command: str,
    result: lldb.SBCommandReturnObject,
    internal_dict: dict[str, object],
) -> None:
    """
    Load the game's PDB symbols.

    Executes:

        target symbols add <pdb>

    Use after opening a dump if symbols were not loaded automatically.

    Example:
        (lldb) load-symbols
    """
    debugger.HandleCommand(f'target symbols add "{PDB}"')


def crash(debugger, command, result, _):
    """
    Show an overview of the crash.

    Performs:
        - selects thread 1
        - selects frame 0
        - prints a backtrace
        - prints frame information
        - prints CPU registers

    This is intended to answer:
        - Where did the program crash?
        - What function crashed?
        - What was the machine state?

    Example:
        (lldb) crash
    """
    cmds = [
        "thread select 1",
        "frame select 0",
        "bt",
        "frame info",
        "register read",
    ]
    for cmd in cmds:
        debugger.HandleCommand(cmd)


def why(debugger, command, result, _):
    """
    Show information useful for determining why the current frame failed.

    Prints:
        - local variables
        - function arguments
        - disassembly of the current function

    Useful for identifying:
        - null pointers
        - invalid objects
        - bad arguments
        - the faulting instruction

    Example:
        (lldb) why
    """
    cmds = [
        "frame variable",
        "disassemble --frame",
    ]
    for cmd in cmds:
        debugger.HandleCommand(cmd)


def args(debugger, command, result, _):
    """
    Show function arguments and local variables with their types.

    Executes:

        frame variable --show-types

    Useful for inspecting function inputs.

    Example:
        (lldb) args
    """
    debugger.HandleCommand("frame variable --show-types")


def locals(debugger, command, result, _):
    """
    Show only local variables.

    Function arguments are omitted.

    Useful when debugging a large function whose arguments are already known.

    Example:
        (lldb) locals
    """
    debugger.HandleCommand("frame variable --no-args")


def this(debugger, command, result, _):
    """
    Print the current C++ object.

    Displays:
        this
        *this

    Useful when stopped inside a member function.

    Example:
        (lldb) this
    """
    debugger.HandleCommand("frame variable this *this")


def spawn(debugger, command, result, _):
    """
    Inspect an object during the spawning pipeline.

    Prints:
        - backtrace
        - caller frame
        - current object

    Intended for debugging crashes during:
        net_Spawn()
        net_Load()
        g_sv_Spawn()
        cl_Process_Spawn()

    Example:
        (lldb) spawn
    """
    debugger.HandleCommand("bt")
    debugger.HandleCommand("up")
    debugger.HandleCommand("frame variable this *this")


def upn(debugger, command, result, _):
    """
    Move up N stack frames and show frame information.

    Default:
        up 1

    Examples:
        (lldb) upn
        (lldb) upn 3
    """
    n = int(command or 1)
    debugger.HandleCommand(f"up {n}")
    debugger.HandleCommand("frame info")


def downn(debugger, command, result, _):
    """
    Move down N stack frames and show frame information.

    Default:
        down 1

    Examples:
        (lldb) downn
        (lldb) downn 2
    """
    n = int(command or 1)
    debugger.HandleCommand(f"down {n}")
    debugger.HandleCommand("frame info")


def source(debugger, command, result, _):
    """
    Show source code around the current execution point.

    Displays approximately twenty lines centered on the current line.

    Useful immediately after selecting a frame.

    Example:
        (lldb) source
    """
    debugger.HandleCommand("source list -c 20")


def asm(debugger, command, result, _):
    """
    Show disassembly around the current instruction.

    Displays roughly thirty instructions surrounding the program counter.

    Useful for:
        - optimized builds
        - missing source
        - verifying compiler output

    Example:
        (lldb) asm
    """
    debugger.HandleCommand("disassemble --pc --count 30")


def pc(debugger, command, result, _):
    """
    Show only the current instruction.

    Useful for quickly identifying the exact instruction that faulted.

    Example:
        (lldb) pc
    """
    debugger.HandleCommand("disassemble --pc --count 1")


def vptr(debugger, command, result, _):
    """
    Print the object's virtual table pointer.

    Useful for detecting:
        - corrupted objects
        - use-after-free
        - incorrect dynamic type

    Must be executed inside a non-static member function.

    Example:
        (lldb) vptr
    """
    debugger.HandleCommand("expression/x *(void**)this")


def sus(debugger, command, result, _):
    """
    Perform a quick sanity check on the current object.

    Prints:
        - this pointer
        - object contents
        - CPU registers
        - nearby assembly

    Intended as a one-command overview when an object appears corrupted.

    Useful for spotting:
        - invalid 'this'
        - overwritten memory
        - register corruption
        - unexpected control flow

    Example:
        (lldb) sus
    """
    cmds = [
        "frame variable this",
        "frame variable *this",
        "register read",
        "disassemble --pc --count 10",
    ]
    for c in cmds:
        debugger.HandleCommand(c)


def __lldb_init_module(
    debugger: lldb.SBDebugger,
    internal_dict: dict[str, object],
) -> None:
    debugger.HandleCommand("command script add -f commands.latest_mdmp latest-mdmp")
    debugger.HandleCommand("command script add -f commands.load_symbols load-symbols")
    debugger.HandleCommand("command script add -f commands.crash crash")
    debugger.HandleCommand("command script add -f commands.why why")
    debugger.HandleCommand("command script add -f commands.args args")
    debugger.HandleCommand("command script add -f commands.locals locals")
    debugger.HandleCommand("command script add -f commands.this this")
    debugger.HandleCommand("command script add -f commands.spawn spawn")
    debugger.HandleCommand("command script add -f commands.upn upn")
    debugger.HandleCommand("command script add -f commands.downn downn")
    debugger.HandleCommand("command script add -f commands.source source")
    debugger.HandleCommand("command script add -f commands.asm asm")
    debugger.HandleCommand("command script add -f commands.pc pc")
    debugger.HandleCommand("command script add -f commands.vptr vptr")
