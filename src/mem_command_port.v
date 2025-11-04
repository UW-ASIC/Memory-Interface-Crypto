/*

Help facilitate communication between our module and other modules on the bus. 

Checks whenever new data is available and send acknowledgements according

The command given to us will be something in this format:

dest id, opcode, address/data

We read all this from the bus and know that the message is meant for us and acknowledge that
we have received this command. We can then pass the command to the Transaction FSM

*/

module command_port (
    //inputs
    input wire clk,
    input wire rst_n,

    input wire [9:0] in_bus,
    output wire [9:0] out_bus,

    //----to FSM----
    input wire in_cmd_fsm_ready,
    output wire out_cmd_fsm_valid,
    output wire [1:0] out_cmd_fsm_opcode,
    output wire [23:0] out_cmd_fsm_addr,

    input wire in_rd_fsm_valid,
    input wire [7:0] in_rd_fsm_data,
    output wire out_rd_fsm_ack,

    output wire out_wr_fsm_valid,
    output wire [7:0] out_wr_fsm_data,
    input wire in_wr_fsm_ready,

    input wire in_fsm_don
);

always @(posedge clk, or negedge rst_n) begin
    
end


endmodule