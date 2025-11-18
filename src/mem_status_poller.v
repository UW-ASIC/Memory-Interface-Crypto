/*

Continuously polls a signal from the SPI controller to check the state of transfer

Once the transfer is done notify FSM of what state to change to

TODO: look into if we can be merged in to the transaction FSM
*/

module status_poller (
    input  wire        clk,
    input  wire        rst_n,

    //----Transaction FSM Connections----
    input wire [7:0] in_total_transfers,

    input wire in_poller_start,

    // Ready to launch more work (used by FSM)
    output wire out_ready, //not ready unless (completed == total)

    // All transactions finished
    output wire [5:0] flags   // 1 = completed == total (no more work)
);

reg[7:0] completed_transfers;

endmodule;
