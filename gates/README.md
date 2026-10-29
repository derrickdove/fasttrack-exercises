# Capstone gates

A gate is a set of checks for your capstone, the small chassis tester you build across the plan. The tests here import your code from `capstone/chassis/`. Write your own small tests in `capstone/tests/` as you build; use a gate to check the block's finished behavior.

Gates are cumulative. **Gate: b3** runs b1, b2, and b3, so an earlier feature still needs to work. `Checks: N / M passed` counts individual tests. An import error means part of your capstone is still missing or cannot load.

Press **Ctrl+Shift+B** and choose **Gate: b1** (or your current block). From a terminal, run `tools\run.ps1 b1` on Windows or `bash tools/run.sh b1` on Linux or Mac. Gate tasks appear as gate folders are added. Authors can set `FT_CAPSTONE` to another capstone folder when checking a reference implementation.
