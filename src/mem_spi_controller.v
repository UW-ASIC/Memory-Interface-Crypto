/*

Dual SPI/QSPI connection to the flash. 

The transaction FSM will tell us what to send to the SPI flash, we just facilitate the transfer of that command/address/data through the SPI port

We’re responsible for SPI things like asserting CS low, start driving SLCK, shift data out_io from MISO, read in_io data from MOSI.
We also responsible setting our internal bit flag to “done” once transaction is complete to tell the status poller we can keep going

Clock Divider / Shifting FSM is already partially implemented by Ryan

*/
module mem_spi_controller (
    input wire clk, 
    input wire rst_n,

    //---- Transaction FSM connections ----
    input wire in_start, //start the transaction
    input wire r_w, //1 is read, 0 is write
    input wire quad_enable, //0 use standard, 1 use quad
    output reg out_busy, //tell the fsm we are busy
    output reg out_done, //tell the fsm we are done

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
// Dump the signals to a VCD file. You can view it with gtkwave or surfer.
initial begin 
    $dumpfile("module_name.vcd"); 
    $dumpvars(0, spi_controller); 
    #1; 
end

localparam DIVIDER = 1; //divider == 1 means half frequency, divider == 2 means quarter frequency 

reg out_sclk_prev = 0;
reg out_sclk_counter;
wire out_sclk_rising;
wire out_sclk_falling;

assign out_sclk_rising = (out_sclk == 1 && out_sclk_prev == 0);
assign out_sclk_falling = (out_sclk == 0 && out_sclk_prev == 1);
wire [4:0] num_cycles;
reg [4:0] cycle_count;
assign num_cycles = (quad_enable) ? 4'b0010 : 4'b1000; //2 cycles if quad enable, 8 cycles if quad enable
reg [1:0] state;
localparam IDLE = 2'b00;
localparam BUSY = 2'b01;
localparam FINISHED = 2'b10;

reg internal_rw;
reg [7:0] internal_data;
reg transaction_done = 0;
//handshake
always @ (posedge clk or negedge rst_n)begin
    if(!rst_n)begin
        internal_data <= 0;
        state <= IDLE;
        out_tx_ready <= 1;
        internal_rw <= 0;
        out_cs_n <= 1;
        out_rx_valid <= 0;
        out_busy <= 0;
        out_done <= 0;
    end else begin
        case(state)
            IDLE: begin
                out_rx_valid <= 0;
                out_tx_ready <= 1;
                out_cs_n <= 1;
                if(in_start) begin
                    internal_data <= in_tx_data;
                    internal_rw <= r_w;
                    out_tx_ready <= 0;
                    state <= BUSY;
                    out_cs_n <= 0;
                    out_busy <= 1;
                end
            end
            BUSY: begin
                out_rx_valid <= 0;
                out_tx_ready <= 0;
                out_cs_n <= 0;
                if(transaction_done) begin
                    out_rx_valid <= 1;
                    state <= FINISHED;
                    out_cs_n <= 1;
                    out_busy <= 0;
                    out_done <= 1;
                end
            end
            FINISHED: begin
                out_rx_valid <= 1;
                out_tx_ready <= 0;
                out_cs_n <= 1;
                if(in_rx_ready) begin
                    out_rx_valid <= 0;
                    out_tx_ready <= 1;
                    state <= IDLE;
                end
            end
            default: begin
                state <= IDLE;
                out_tx_ready <= 1;
                out_rx_valid <= 0;
                out_cs_n <= 1;
            end
        endcase
    end
end


//generate out_sclk
always @ (posedge clk or negedge rst_n) begin
    if(!rst_n)begin
        out_sclk <= 0;
        out_sclk_prev <= 0;
        out_sclk_counter <= 0;
    end else begin
        if(state == BUSY)begin
            out_sclk_prev <= out_sclk;
            if(out_sclk_counter == DIVIDER - 1)begin
                out_sclk <= ~out_sclk;
                out_sclk_counter <= 0;
            end else begin
                out_sclk_counter <= out_sclk_counter + 1;
            end
        end else begin
            out_sclk <= 0;
            out_sclk_counter <= 0;
            out_sclk_prev <= 0;
        end
    end
end

//interact with flash
always @ (posedge clk or negedge rst_n) begin
    if(!rst_n)begin
        transaction_done <= 0;
        out_rx_data <= 0;
        cycle_count <= 0;
        io_ena <= 0;
    end else if(state == BUSY)begin 
        if(cycle_count == num_cycles - 1)begin
            transaction_done <= 1;
            cycle_count <= 0;
        end else begin
            cycle_count <= cycle_count + 1;
            transaction_done <= 0;
        end
        if(!internal_rw) begin //read on rising sclk edge
            if(out_sclk_rising)begin
                if(quad_enable) out_rx_data <= {out_rx_data[3:0], in_io[3:0]}; //read 4 bits at a time
                else out_rx_data <= {out_rx_data[6:0], in_io[0]}; //read one bit at a time
            end
        end else begin //write on falling sclk edge
            if (out_sclk_falling)begin
                io_ena <= 4'b1111;
                if(quad_enable) out_io[3:0] <= internal_data[cycle_count*4 +: 4]; //shift out data on all 4 wires
                else out_io[0] <= internal_data[cycle_count]; //shift data only on 1 wire
            end else io_ena <= 0;
        end
    end else begin //idle or finished state
        transaction_done <= 0;
        cycle_count <= 0;
        io_ena <= 0;
    end
end
endmodule
