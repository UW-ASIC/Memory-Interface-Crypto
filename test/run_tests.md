## Running the tests:

## First put this after port declarations inside of your .v file:

```verilog
    // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
    initial begin
        $dumpfile("module_name.vcd");
        $dumpvars(0, module_name);
    end
```

```bash
make TOPLEVEL=your_module MODULE=your_module PROJECT_SOURCES=your_module.v TESTCASE = <optional>
ex:
make TOPLEVEL=mem_transaction_fsm MODULE=test_mem_transaction_fsm PROJECT_SOURCES=mem_transaction_fsm.v TEST_CASE=test_rd_key
```
