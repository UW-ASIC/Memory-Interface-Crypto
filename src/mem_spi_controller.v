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
    input wire [7:0] in_num_bytes,
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

module QSPI_controller (
    input clk,
    input rst_n,
    input [7:0] data_in,
    input r_w,
    output reg [7:0] data_out,
    input [1:0] width,
    input valid,
    output reg ready,
);
localparam WIREWIDTH_1 = 2'b00;
localparam WIREWIDTH_2 = 2'b01;
localparam WIREWIDTH_4 = 2'b11;
localparam DIVIDER = 2; //idk

reg sck = 0;
reg sck_prev = 0;
reg sck_counter;
reg [3:0] io;
reg n_cs = 1;
wire [4:0] num_cycles;
reg [4:0] cycle_count;
assign num_cycles = (width == WIREWIDTH_1) ? 4'b0111 : 
                    (width == WIREWIDTH_2) ? 4'b0011 :
                                             4'b0010;
reg transaction_complete = 0;
//generate sck
always @ (posedge clk or negedge rst_n) begin
    if(!rst_n)begin
        n_cs <= 1;
        sck <= 0;
        sck_prev <= 0;
        sck_counter <= 0;
    end else begin
        if(valid && !transaction_complete)begin
            n_cs <= 0;
            sck_prev <= sck;
            if(sck_counter == DIVIDER - 1)begin
                sck <= ~sck;
                sck_counter <= 0;
            end else begin
                sck_counter <= sck_counter + 1;
            end
        end else begin
            n_cs <= 1;
            sck <= 0;
            sck_prev <= 0;
            sck_counter <= 0;
        end
    end
end

always @ (posedge clk or negedge rst_n) begin
    if(!rst_n){
        transaction_complete <= 0;
        ready <= 0;
        data_out <= 0;
    }
    if(!r_w){ //read on rising sck edge
        if(cycle_count >= num_cycles)begin
            transaction_complete <= 1;
            ready <= 1;
        end else begin
            ready <= 0;
            transaction_complete <= 0;
            if(!sck_prev && sck)begin
                case(width)
                    WIREWIDTH_1: begin
                        //shift in data one bit at a time
                        data_out <= {data_out[6:0], io[0]};
                    end
                    WIREWIDTH_2: begin
                        //shift in data 2 bits at a time
                        data_out <= {data_out[5:0], io[1:0]};
                    end
                    WIREWIDTH_4: begin
                        //shift in data 4 bits at a time
                        data_out <= {data_out[3:0], io[3:0]};
                    end
                endcase
                cycle_count <= cycle_count + 1;
            end
        end
    }else{//write on falling sck edge
        if(cycle_count >= num_cycles) begin
            transaction_complete <= 1;
            ready <= 1;
        end
        if(sck_prev && !sck)begin
            transaction_complete <= 0;
            ready <= 0;
            case(width)
                WIREWIDTH_1: begin
                    //shift in data one bit at a time
                    io[0] <= data_in[cycle_count];
                end
                WIREWIDTH_2: begin
                    //shift in data 2 bits at a time
                    io[1:0] <= data_in[cycle_count*2 +: 2];
                end
                WIREWIDTH_4: begin
                    //shift in data 4 bits at a time
                    io[3:0] <= data_in[cycle_count*4 +: 4];
                end
            endcase
            cycle_count += 1;
        end
    }
end

endmodule