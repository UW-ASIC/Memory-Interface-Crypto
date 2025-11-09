/*

Dual SPI/QSPI connection to the flash. 

The transaction FSM will tell us what to send to the SPI flash, we just facilitate the transfer of that command/address/data through the SPI port

We’re responsible for SPI things like asserting CS low, start driving SLCK, shift data out from MISO, read in data from MOSI.
We also responsible setting our internal bit flag to “done” once transaction is complete to tell the status poller we can keep going

Clock Divider / Shifting FSM is already partially implemented by Ryan

*/
module spi_controller (
    input wire clk, 
    input wire rst_n,

    //---- Transaction FSM connections ----
    input wire in_start,
    input wire [15:0] in_num_bytes,
    output wire out_busy,
    output wire out_done,

    //Send, MOSI side for write text commands
    input wire in_tx_valid,
    input wire [7:0] in_tx_data,
    output wire out_tx_ready,

    //Recv, MISO side for read key, read text commands
    input wire out_rx_valid,
    output wire [7:0] out_rx_data,
    input wire in_rx_ready,

    //---- SPI flash connections ----
    output wire out_sclk,
    output wire [3:0] out_io,
    input wire [3:0] in_io,
    output wire out_cs_n,
    output wire [3:0] io_ena
);
    
endmodule