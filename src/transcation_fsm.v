/*

Take 8 bit bit command input and convert that command into format SPI flash can understand

Send signal to SPI controller whenever the controller is ready

The SPI flash generally follows this sequence of data transfer

The flash has it’s own opcodes and also a cache you can load to for fast access. We want to turn a “read from this address” command into opcodes and address the SPI flash can understand. 

We will decode it to packets like this and send to the SPI controller whenever the status poller tells us it’s ready:command, data, dummy, data

*/
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