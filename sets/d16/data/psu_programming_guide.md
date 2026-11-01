# PSU-30 programming guide: remote power-up excerpt

Original training text for a fictional bench power supply. A **limit** is the
maximum allowed voltage or current. Voltage is measured in **volts** (V), and
current (electric charge flowing per second) in **amperes**, or **amps** (A).
The **output** is the connection that delivers power to the equipment under test.
Keep the output OFF while changing either limit.

Send one text command at a time. A command ending in `?` requests a text reply.
The connection supplies message endings; the caller sends no newline here.

| Command | Meaning for this model |
| --- | --- |
| `*IDN?` | Identify the supply: `FastTrack,PSU-30,<serial>,<firmware>`. These four comma-separated fields name the maker, model, unique unit number, and installed software version. |
| `*RST` | Reset settings to their starting values and turn the output OFF. Does not clear the error queue. |
| `*CLS` | Clear stored status events and the error queue. Does not reset voltage or current settings. |
| `*OPC?` | Operation complete query: wait until earlier commands finish, then reply `1`. A connection timeout raises an exception instead of waiting forever. |
| `*ESR?` | Read and clear the event status register (a stored integer recording instrument events). Does not remove error-queue entries. Not needed in this power-up procedure. |
| `SYST:ERR?` | Remove and return the oldest queued error as `code,"message"`. A nonzero integer code means failure. An empty queue returns `0,"No error"`. Messages may contain commas. |
| `CURR <amps>` | Set the current limit, from 0 to 3 A, with output OFF. |
| `VOLT <volts>` | Set the voltage limit, from 0 to 30 V, with output OFF. |
| `OUTP OFF` / `OUTP ON` | Disable / enable power delivery. |

The five `*` commands above are **IEEE 488.2 common commands**: standardized
command names shared by many instrument types. The other commands and this
model's reset behavior and allowed limits must be checked in its own guide.

For station startup: verify maker and model using `*IDN?`; send `*RST`, then
`*CLS`, then explicitly `OUTP OFF`. Set `CURR` before `VOLT`. Wait for the `1`
reply from `*OPC?`. Read `SYST:ERR?` until its code is zero; stop immediately
on the first nonzero code and report its code and message. Only an empty error
queue permits `OUTP ON`. Clearing status after setting limits would erase
errors you need to check, so do not send another `*CLS` during this procedure.
