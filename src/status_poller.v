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