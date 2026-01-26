/*

Dual SPI/QSPI connection to the flash. 

The transaction FSM will tell us what to send to the SPI flash, we just facilitate the transfer of that command/address/data through the SPI port

We’re responsible for SPI things like asserting CS low, start driving SLCK, shift data out_io from MISO, read in_io data from MOSI.
We also responsible setting our internal bit flag to “done” once transaction is complete to tell the fsm we can keep going

Clock Divider / Shifting FSM is already partially implemented by Ryan

*/

// sample on risedge shift on falledge
`default_nettype none
`timescale 1ns/1ps
module mem_spi_controller (
    input wire clk, 
    input wire rst_n,

    //---- Transaction FSM connections ----
    input wire in_start, //start the transaction
    input wire r_w, //1 is read, 0 is write
    input wire quad_enable, //0 use di/do only, 1 use 4 pins for input/output, even in qspi mode sending opcdode and addr is still 1 pins
    output reg out_done, //tell the fsm we are done
    input wire qed, // 1 means qspi mode, 0 means standard spi

    //Send, MOSI side for write text commands
    input wire in_tx_valid, //the fsm data is valid
    input wire [7:0] in_tx_data, //the data to send to the flash
    output reg out_tx_ready, //tells fsm controller is ready to send data

    //Recv, MISO side for read key, read text commands
    output reg out_rx_valid, //tell the fsm the out_data is valid
    output reg [7:0] out_rx_data, //data to send to fsm
    input wire in_rx_ready, //fsm tells the controller it is ready to receive the data

    //---- SPI flash connections ----
    output reg out_sclk,
    output reg [3:0] out_io,
    input wire [3:0] in_io,
    output reg out_cs_n,
    output reg [3:0] io_ena
);

    localparam DIVIDER = 3; //divider == 1 means half frequency, divider == 2 means quarter frequency 
    localparam T_SETUP_HOLD_CYC = 1; // setup/hold time cycle constant

    reg [3:0] bit_count = 4'b0;
    reg [1:0] sclk_cnt;

    wire sclk_toggle = (sclk_cnt == DIVIDER -1); //pulse when sclk toggle
    wire sclk_fall = sclk_toggle && (out_sclk == 1'b1); // f edge detection
    wire sclk_rise = sclk_toggle && (out_sclk == 1'b0); // r edge detection

    wire [3:0] num_cycles;
    assign num_cycles = internal_quad ? 4'b0010 : 4'b1000; //2 cycles if quad enable, 8 cycles if quad enable

    reg [1:0] t_cnt  = 2'b0; // setup/hold time count

    reg t_met;

    reg internal_rw; // latched r_w for this byte
    wire internal_quad = quad_enable && qed; // latched quad_enable for this byte
    reg [7:0] tx_shift; // byte to shift out in write mode
    reg have_tx_byte; // tx_shift is loaded
    reg [7:0] rx_shift; // rx shift reg
    reg rx_full; // rx shift is full

    reg active = 1'b0; // 1 = CS low, transaction in progress

    assign out_tx_ready = ~have_tx_byte; // comb drive tx ready
    // cs driving, cs should be low when in_start is high
    // read/write latch
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active   <= 1'b0;
            out_cs_n <= 1'b1;
            internal_rw   <= 1'b0; 
        end else begin
            // start transaction
            if (in_start) begin
                active <= 1'b1;
                internal_rw <= r_w;
            end 
            // end transaction fsm dropped in_start sclk high
            if (!in_start && (out_sclk == 1'b1))
                active <= 1'b0;

            out_cs_n <= ~active;
        end
    end
    // tx handshake
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_shift      <= 8'h00;
            have_tx_byte  <= 1'b0;
        end else begin
            // data latch handshake
            if (out_tx_ready && in_tx_valid) begin
                tx_shift <= in_tx_data;
                have_tx_byte <= 1'b1;
            end
            if (out_done)
                have_tx_byte <= 1'b0;

        end    
    end
    // rx handshake
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_shift <= 8'h00;
            rx_full <= 1'b0;
            out_rx_data <= 8'b0; 
            out_rx_valid <= 1'b0;
        end else begin
            out_rx_valid <= rx_full;
            //load data to rx 
            if (out_done && internal_rw == 1'b1) begin
                out_rx_data <= rx_shift;
            end
            // clear rx full when fsm handshake 
            if (rx_full && in_rx_ready)
                rx_full <= 1'b0;
        end
    end
    //sclk toggling and bit shifting
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_sclk <= 1'b1;
            sclk_cnt <= 0;
            bit_count <= 0;
            out_done <= 1'b0;
        end else if (active) begin
            // default 
            out_done <= 1'b0;
            if  ( (!internal_rw && !have_tx_byte) || (internal_rw && rx_full) ) begin
                out_sclk  <= 1'b1;
                sclk_cnt  <= 0;
                bit_count <= 0;
            end else begin
                if (sclk_cnt == DIVIDER - 1) begin
                    sclk_cnt <= 0;
                    out_sclk <= ~out_sclk;

                    // shift out on fall edge
                    if(sclk_fall && !internal_rw && have_tx_byte && t_met) begin
                        // quad/single
                        if (internal_quad) begin
                            out_io <= tx_shift[7:4];
                            tx_shift <= tx_shift << 4; // msb to lsb
                        end else begin
                            out_io[0] <= tx_shift[7]; // do is io0
                            tx_shift <= tx_shift << 1; // msb to lsb
                        end
                    end

                    // sample on rise edge
                    if(sclk_rise && internal_rw && !rx_full && t_met) begin
                        // quad/single
                        if (internal_quad) begin
                            rx_shift <= {rx_shift[3:0],in_io}; // msb to lsb
                        end else begin
                            rx_shift <= {rx_shift[6:0],in_io[1]}; // msb to lsb
                        end
                    end
                    // bit counter 
                    if (sclk_rise && ((internal_rw && !rx_full) || (!internal_rw && have_tx_byte))) begin
                        if (bit_count == num_cycles - 1) begin
                            bit_count <= 0;
                            out_done <= 1;
                            if (internal_rw) begin
                                rx_full <= 1'b1;
                            end
                        end else begin
                            bit_count <= bit_count + 1;
                        end
                    end 
                end else begin
                    sclk_cnt <= sclk_cnt + 1;
                end            
            end

        end else begin
            out_sclk <= 1'b1;
            sclk_cnt <= 0;
            bit_count <= 0;
            out_done <= 1'b0;        
        end
    end

    // io ena / output when read
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            io_ena <= 4'b0;
            out_io <= 4'b1100;
        end else begin
            if (!qed) begin
                io_ena[3:2] <= 2'b11; // io 2, io 3 active low
                out_io[3:2] <= 2'b11; 
                // single spi mode
                io_ena[1] <= 1'b0; // di always read
                io_ena[0] <= 1'b1; // do always write
            end else begin
                if (active) begin
                    if (internal_quad) begin
                        io_ena <= internal_rw ? 4'b0000:4'b1111; // if internal quad then tristate all io pins
                    end else begin
                        io_ena <= internal_rw ? 4'b0000:4'b0001; // internal single 
                    end               
                end else begin
                    io_ena <= 4'b0000;
                end
            end
        end
    end
    
    // timing requirement for setup/hold 10ns
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            t_met <= 1'b0;
            t_cnt <= 2'b0; 
        end else begin
            if (active) begin
                if (sclk_toggle) begin
                    t_cnt <= 2'b0;
                    t_met <= 1'b0;
                end else begin
                    if (t_cnt == (T_SETUP_HOLD_CYC-1)) begin
                        t_met <= 1'b1;
                    end else begin
                        t_cnt <= t_cnt + 1;
                    end
                end
            end else begin
                t_cnt <= 2'b0;
                t_met <= 1'b0;
            end
        end
    end

endmodule
