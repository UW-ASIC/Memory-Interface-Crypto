//responsible for translating command port data to SPI transactions
//pass the data back to the command port
module transaction_fsm(
    input wire clk,
    input wire rst,
    input wire transaction_status,
    input wire read_write,
    input wire [7:0] cmd_port_data_in, 
    input wire [7:0] spi_port_data_in,

    output wire [7:0] cmd_port_data_out,
    output wire [7:0] spi_port_data_out
);

    

endmodule