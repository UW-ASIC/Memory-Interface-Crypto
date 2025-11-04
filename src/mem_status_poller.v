/*

Continuously polls a signal from the SPI controller to check the state of transfer

Once the transfer is done notify FSM of what state to change to

TODO: look into if we can be merged in to the transaction FSM
*/

module status_poller #(
    flag_len = 2;
)
(
    input wire clk,
    input wire rst_n,
    input wire [3:0] length,
    input wire [3:0] opcode,
    input wire read_write,

    output wire transcation_complete, 
    output wire [flag_len - 1:0] flags,
    output wire [flag_len - 1:0] flags
)

endmodule;