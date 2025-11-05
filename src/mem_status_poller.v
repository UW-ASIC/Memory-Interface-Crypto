/*

Continuously polls a signal from the SPI controller to check the state of transfer

Once the transfer is done notify FSM of what state to change to

TODO: look into if we can be merged in to the transaction FSM
*/

module status_poller (
    input  wire        clk,
    input  wire        rst_n,

    //----Transaction FSM Connections----
    input  wire [15:0] in_transactions_completed,
    input  wire [15:0] total_transactions,

    // Ready to launch more work (used by FSM)
    output wire ready //not ready unless (completed == total)

    // All transactions finished
    output wire all_done_valid   // 1 = completed == total (no more work)
);


endmodule;