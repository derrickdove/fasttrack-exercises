# d48 - Reading and changing C++ driver code

**Time:** about 62 minutes (including 5 minutes to read the supplied code) | **Read first:** learncpp 12.7, [Introduction to pointers](https://www.learncpp.com/cpp-tutorial/introduction-to-pointers/); learncpp 14.2, [Introduction to classes](https://www.learncpp.com/cpp-tutorial/introduction-to-classes/); *The Linux Command Line*, chapter 11, [The Environment](https://linuxcommand.org/tlcl.php) (variables and PATH). Companion: *C++ Primer*, chapter 7, Classes. **You edit:** `starter/psu_driver.cpp`.

## What you're building

A **driver** translates station software requests into instrument operations. This driver belongs to a **PSU** (power supply unit), the instrument providing voltage and limiting current to the hardware under test. Voltage is electrical potential difference, measured in **volts** (V). Repair its voltage guard, decode its error replies, limit operator current requests, and release its connection when a test step ends. All tests use a **fake**, a small substitute for an instrument connection; no hardware is needed.

## How this works

1. Read `include/psu_driver.h` (the declarations: names and types) and `starter/psu_driver.cpp` (the definitions: executable bodies). Change only the E1-E5 bodies in the `.cpp` file, including the E5 destructor. For E2 and E3, restore the commented parameter names (`/*reply*/` becomes `reply`) and replace the `throw std::logic_error(...)` stubs. E1 has a seeded bug; E4 has missing teardown. Keep the supplied helpers and declarations. Don't edit `tests/`.
2. Save your changes and run `bash tools/run.sh d48` in your WSL terminal. **Ctrl+Shift+B -> Test: d48** is a shortcut. In native Windows PowerShell, run `powershell -NoProfile -ExecutionPolicy Bypass -File tools\run.ps1 d48`. At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise. Each exercise has several test cases; every case must pass.
3. Report **all pass / partial / stuck** in the tracker.

A **compiler** turns C++ source into a program. In WSL2 Ubuntu, the root README's setup installs `build-essential`, the Ubuntu package that supplies the `g++` compiler and build tools. If it is missing, run `sudo apt-get update && sudo apt-get install -y build-essential` in Ubuntu before starting. The runner uses C++20 (the language edition), finding `clang++` or `g++` on Linux/Mac.

**Native Windows alternative:** install Visual Studio Build Tools with **Desktop development with C++**. On Windows the runner prefers those tools, then tries `g++` if available. Python 3.12+ runs the shared build helper; no extra Python packages are needed for this set. **doctest** is the bundled C++ test library, separate from Python's similarly named library.

An **environment variable** is a named value inherited by child programs. **PATH** is the environment variable listing directories searched for programs such as `g++`; reopen the terminal after changing it. In Bash, `command -v g++` locates that compiler and `export CXX=g++` selects it on Linux/Mac. `FT_PYTHON` can select the Python executable used by either runner.

A **class** combines stored values (**members**) and functions (**methods**); `public` allows callers to use a member and `private` limits access to class code. A **constructor** initializes an object; `~PsuDriver()` is its **destructor**, called automatically when the object leaves its block. **Teardown** is releasing resources after a test, including when that test fails.

A **session** is an open instrument connection; the supplied `Session` class describes its **interface**, the methods a connection must support. A **pointer** holds an object's address; `nullptr` means no object and `->` calls a method through a pointer. A **borrowed pointer** means someone else owns the object: use it but never `delete` it. Here, the caller must keep `Session` alive longer than `PsuDriver`. A **virtual** method lets a test fake supply its own implementation; `override` checks that it matches. Copying this driver is disabled in the header to prevent duplicate cleanup.

```cpp
struct Indicator { bool lit = false; };
Indicator lamp;
Indicator* pointer = &lamp; // & takes the address of lamp.
if (pointer != nullptr) {
    pointer->lit = true;
}
```

An **exception** interrupts normal execution: `throw std::invalid_argument("reason")` rejects a bad argument. `try { ... } catch (...) { ... }` catches any exception type. `noexcept` promises that none will escape; violating it terminates the program. **Stack unwinding** is destroying local objects while an exception travels to its caller.

`double` is a floating-point number; **finite** excludes positive/negative infinity and **NaN** (not a number). `std::isfinite` checks this. `const std::string&` reads a string without copying or changing it. An `ErrorReply` contains `.code` (an `int`, a whole number) and `.message` (a `std::string`, text). The supplied includes provide all needed standard library tools.

## Exercises

### E1 - Guard the station's voltage command (easy, ~8 min)

**Goal:** Fix the range check before an unsafe voltage command reaches the PSU.

**Signature:** `std::string formatSetVoltage(double volts)`

**Contract:** Accept only finite values in the inclusive range 0 through 30 volts. Reject every other value with `std::invalid_argument`; its message is up to you. Return the supplied `voltageCommand(volts)` result for accepted values: `VOLT `, exactly three decimal places, and one newline (`\n`). The helper already handles formatting, the decimal point, and negative zero. Change the guard; keep the helper call.

**Example:** `formatSetVoltage(12.5)` -> `"VOLT 12.500\n"`; `30.0` is valid, `30.001` throws.

**Watch out:** `&&` means both conditions; `||` means either condition. NaN fails ordinary ordered comparisons, so range comparisons alone are insufficient.

**Reread:** learncpp 14.2, declarations versus definitions, to locate the function body being changed; *The Linux Command Line* ch. 11, examining the environment, if the compiler cannot be found.

### E2 - Decode the PSU's error reply (medium, ~17 min)

**Goal:** Convert one error reply into an `ErrorReply` for the station report. A code of zero means no error.

**Signature:** `ErrorReply parseErrorReply(const std::string& reply)`

**Contract:** **ASCII** is the basic character set containing English letters, digits, and control characters. Remove only surrounding ASCII whitespace (space, tab `\t`, carriage return `\r`, newline `\n`, vertical tab `\v`, form feed `\f`). The rest must be an optional `+` or `-`, one or more ASCII digits `0`-`9`, a comma, and a double-quoted message. No spaces may appear within the number or beside the comma. Leading zeroes are allowed. The code must fit `int` (`std::numeric_limits<int>::min()` through `max()` from `<limits>`). Return the numeric `.code` and the unquoted `.message`.

The message may be empty or contain commas, spaces, tabs, and ordinary backslashes; preserve its text exactly. It must contain no double quote, `\r`, or `\n`. Escaped quotes have no special meaning and are rejected. Reject every malformed reply, including integer overflow, with `std::invalid_argument` (message up to you). This is d05 E2's grammar, with C++'s bounded integer range and ASCII surrounding whitespace.

**Examples:** `"-113,\"Undefined header\""` -> `{-113, "Undefined header"}`; `" \t+0,\"No error\"\r\n"` -> `{0, "No error"}`; `"12,\"CH1, overload\""` -> `{12, "CH1, overload"}`.

**Supplied helpers (keep them):** `trimAscii(text)` returns a copy with only surrounding ASCII whitespace removed; empty or all-whitespace input returns `""`. `toInt(text)` accepts exactly an optional sign followed by ASCII digits, including leading zeroes, and returns an `int`. It throws `std::invalid_argument` for malformed text or overflow. Call it directly: you do not need to use `std::stoi`, regular expressions, or catch conversion exceptions.

**String tools:** A **position** counts characters from zero. `find(character)` returns the first matching position, or `std::string::npos` if absent. Always check for `npos` before splitting. `substr(start, count)` copies `count` characters; omitting `count` copies to the end. For an unrelated station label:

```cpp
const std::string label = "rack:READY";
const auto colon = label.find(':');
if (colon == std::string::npos) { throw std::invalid_argument("missing colon"); }
const std::string name = label.substr(0, colon); // "rack"
const std::string state = label.substr(colon + 1); // "READY"
```

**Steps (~17 minutes with helpers):** Trim the whole reply, split at its first comma, and pass the number portion unchanged to `toInt`. For the remaining portion, `size()` counts characters and `front()` / `back()` read the first / last character. Check that its size is at least 2 before checking those characters for double quotes (`'"'`). If you name that portion `quoted`, remove the two outer quotes with `quoted.substr(1, quoted.size() - 2)`. Then `message.find_first_of("\"\r\n")` finds any forbidden quote, carriage return, or newline; `npos` means none are present. Throw `std::invalid_argument` for a failed check. Preserve the message's whitespace and backslashes. Return `{code, message}` to build the result.

**Reread:** learncpp 14.2, defining and accessing class members, for the result object's fields; *C++ Primer* ch. 7, defining classes, for the supplied `ErrorReply` structure.

### E3 - Limit the operator's current request (easy, ~8 min)

**Goal:** **Clamp** a requested current, meaning keep it within the allowed interval, before a station applies it.

**Signature:** `double clampCurrent(double requestedAmps, double limitAmps)`

**Contract:** Both inputs must be finite and `limitAmps` must be nonnegative; otherwise throw `std::invalid_argument` (message up to you). With valid inputs, return zero for a request below zero, `limitAmps` for a request above the limit, and the request unchanged otherwise. Endpoints are included; a zero limit is valid. Values are in **amperes** (amps), the unit of electric current. No formatting or instrument calls are needed.

**Example:** `clampCurrent(7.0, 3.0)` -> `3.0`; `clampCurrent(-0.5, 3.0)` -> `0.0`; `clampCurrent(1.25, 3.0)` -> `1.25`.

**Watch out:** Check validity before clamping. `std::clamp(value, low, high)` is available from `<algorithm>` once the bounds are valid.

**Reread:** learncpp 14.2, member versus non-member functions: this numerical helper has no stored session state.

### E4 - Close the connection safely (medium, ~12 min)

**Goal:** Make teardown safe when a test fails or the PSU cable has been disconnected.

**Signature:** `PsuDriver::~PsuDriver() noexcept`

**Contract:** If `session_` is `nullptr`, do nothing. Otherwise call `session_->close()` exactly once when the driver is destroyed. Catch and discard every exception from that call, including types unrelated to `std::exception`. Never delete the borrowed session, retry close, or throw from the destructor. The caller's session stays alive after the driver leaves its block. The supplied constructor and header need no changes.

**Example:** `{ PsuDriver driver(&session); }` closes `session` once. If `close()` throws while a measurement exception is already unwinding, the measurement exception must still reach its caller.

**Watch out:** Checking the pointer must happen before using `->`. A destructor still runs during failure handling; an escaping cleanup exception would terminate the station process.

**Reread:** learncpp 12.7, pointers and dereferencing (using a pointed-to object); learncpp 14.2, class members and access; *C++ Primer* ch. 7, class interfaces and constructors.

### E5 - What `static` means in C and C++ (easy-medium, ~12 min)

**Goal:** Give every PSU command a shared sequence number (a number that increases for each command), and count how many PSU command-driver objects are open. Use the separate `PsuCommandDriver` class so E4's session cleanup stays as it is. This small driver prepares command-log text; it does not contact hardware.

**Signature:** `int nextSequence()`; `PsuCommandDriver::PsuCommandDriver()`; `PsuCommandDriver::~PsuCommandDriver() noexcept`; `int PsuCommandDriver::openCount()`; `std::string PsuCommandDriver::tagCommand(const std::string& command)`. The `static` keyword on `openCount()` belongs in the supplied class declaration; omit it in the `.cpp` definition.

**Three meanings of `static`:**

- A **function-local static variable** is declared inside a function. It is initialized once, the first time execution reaches its declaration, and keeps its value between calls. An ordinary local variable is initialized afresh on each call. For example, `static bool ready = false;` inside a function retains later changes to `ready`.
- A **static data member** belongs to the class and is shared by all its objects. Here, the private `openCount_` is that shared variable; its supplied `.cpp` definition starts it at zero. A **static member function**, such as `openCount()`, can read it without needing an object: call `PsuCommandDriver::openCount()`. The `::` operator names a member of a class.
- A **file-scope static function** is declared outside every function and class. Its name has **internal linkage**, meaning other `.cpp` files cannot call that helper by its name. The supplied `taggedCommand(sequence, command)` helper demonstrates this: it is defined only in `psu_driver.cpp`, with `static` before its return type. This restricts the name's visibility; it does not make the function remember values. Function-local and file-scope `static` also exist in C; classes and static class members are C++ features.

**Contract:** Replace the E5 throwing stubs in `starter/psu_driver.cpp` and fill in the E5 destructor's missing decrement. Keep E1-E4 and the supplied E5 helper, header, and zero-initialized counter definition.

1. `nextSequence()` must use a function-local `static int`, initially zero. Increment it before returning, so calls return 1, 2, 3, and so on. There is one sequence shared by direct calls and every driver object. Constructing or destroying a driver must not reset or consume a sequence number.
2. Each successfully constructed `PsuCommandDriver` adds one to `openCount_`; its destructor subtracts one. Here, **open** means constructed and not yet destroyed, even if no commands have been tagged. `openCount()` returns the current shared count without changing it; it starts at zero. Nested blocks and stack unwinding must restore the previous count. No session calls or exceptions are needed. Copying these objects is already disabled in the header.
3. Each `tagCommand(command)` call takes exactly one number from `nextSequence()` and passes that number and `command` to the supplied file-scope `taggedCommand` helper. Return its result: decimal sequence number, colon, one space, then the command text unchanged. Preserve any newline already in the command; add none. Empty text is valid and still takes one sequence number. Tagging does not change the open count.

Calls in this exercise run one at a time, and sequence numbers remain within the range of `int`.

**Example:** In a fresh program, before any other sequence calls:

```cpp
nextSequence(); // 1
nextSequence(); // 2
PsuCommandDriver::openCount(); // 0
{
    PsuCommandDriver outer;
    PsuCommandDriver::openCount(); // 1
    outer.tagCommand("VOLT 12.500\n"); // "3: VOLT 12.500\n"
    {
        PsuCommandDriver inner;
        PsuCommandDriver::openCount(); // 2
    }
    PsuCommandDriver::openCount(); // 1
}
PsuCommandDriver::openCount(); // 0
nextSequence(); // 4: destroying drivers did not reset the sequence
```

**Watch out:** `++value` increments before producing the value; `value++` produces the old value before incrementing. A plain local sequence variable would restart on every call. A non-static count field would give each object its own count. Keep the destructor non-throwing: its starter is a missing-operation comment, like E4, rather than a throwing stub because it is `noexcept`.

**Reread:** The three meanings above; learncpp 14.2, class declarations and definitions; *C++ Primer* ch. 7, static class members.
