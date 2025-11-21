# make TOPLEVEL=mem_transaction_fsm MODULE=test_mem_transaction_fsm PROJECT_SOURCES=mem_transaction_fsm.v

put this after port declarations inside of your .v file
    // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
    initial begin
        $dumpfile("module_name.vcd");
        $dumpvars(0, module_name);
        #1;
    end
