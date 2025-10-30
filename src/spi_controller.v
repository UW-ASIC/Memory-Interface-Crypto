/*

Dual SPI/QSPI connection to the flash. 

The transaction FSM will tell us what to send to the SPI flash, we just facilitate the transfer of that command/address/data through the SPI port

We’re responsible for things like asserting CS low, start driving SLCK, shift data out from MISO, read in data from MOSI, sets bit flag to “done” once transaction is complete

Clock Divider / Shifting FSM is already partially implemented by Ryan

*/
module spi_controller (
    input wire clk, 
    input wire rst_n,
    input wire done,
    input wire [7:0] address, //or [23:0] address
    input wire [7:0] data
);
    
endmodule