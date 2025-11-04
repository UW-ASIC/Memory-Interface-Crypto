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
    
    //----Command Port Connections----
    input wire in_cmd_valid,
    input wire [1:0] in_cmd_opcode,
    input wire [23:0] in_cmd_addr,
    output wire out_fsm_cmd_ready,

    input wire in_wr_data_valid,
    input wire [7:0] in_cmd_data,
    output wire out_fsm_data_ready,

    output wire out_wr_cp_data_valid,
    output wire [7:0] out_wr_cp_data,
    input wire in_wr_cp_ready,

    //----SPI Controller Connections----
    output wire out_spi_start,
    output wire [15:0] out_spi_num_bytes,
    input wire in_spi_busy, 
    input wire in_spi_done,

    //data to SPI Controller
    output wire out_spi_tx_valid,
    output wire [7:0] out_spi_tx_data,
    input wire in_spi_tx_ready,

    //data from SPI Controller
    input wire in_spi_rx_valid,
    input wire [7:0] in_spi_rx_data,
    output wire out_spi_rx_ready,

    //---- Status Poller----
    //TODO: determine how status poller should interface with this module

);

    

endmodule