`default_nettype none

module shift_engine (
    input wire clk,
    input wire [7:0] tx_byte, // input 
    input wire sclk_tick, // sclk divider
    input wire rst_n, // active low async rst
    input wire ena, // enable
    input wire miso, // do from chip
    input wire read, // read ena signal
    input wire sclk_rise, //sclk rising edge
    input wire sclk_fall, //sclk falling edge

    output reg sclk, // sclk
    output reg [7:0] rx_byte, //output byte
    output reg mosi, // di to chip
    output reg ready,   // ready signal for mosi
    output reg done // done signal for miso

);
    
    reg [3:0] tx_cnt,rx_cnt; //byte counter for bit shifting/collecting to mosi/from mosi
    reg [7:0] rx_shift, tx_shift; // shift register

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk <= 0;
            rx_byte <= 8'b0;
            ready <= 0;
            mosi <= 0;
            done <= 0;
            tx_cnt <= 4'b0;
            rx_cnt <= 4'b0;
            rx_shift <= 8'd0;
            tx_shift <= 8'd0;
        end else if(ena) begin
            if (sclk_tick) begin
                sclk <= ~sclk;  
            end
            //msb
            tx_shift <= (tx_cnt == 0)? tx_byte : tx_shift;
            if (sclk_fall) begin
                tx_cnt <= (tx_cnt == 7) ? tx_cnt+1:0;
                mosi <= tx_shift[7];
                tx_shift <= tx_shift <<1;
            end
            // msb first
            if (sclk_rise && read) begin
                if (rx_cnt == 7) begin
                    rx_cnt <= 0;
                    rx_byte <= {rx_shift[6:0],miso}; 
                end else begin
                    rx_cnt++;
                    rx_shift <= {rx_shift[6:0],miso}
                end
            end
            ready <= tx_cnt == 7 ? 1:0;
            done <= rx_cnt == 7? 1:0;
        end else begin
            sclk <= 0;
            rx_byte <= 8'b0;
            mosi <= 0;
            tx_cnt <= 4'b0;
            rx_cnt <= 4'b0;
            sync_di<=2'b0;
            rx_shift <= 8'd0;
            tx_shift <= 8'd0;
            ready <= 0;
            done <= 0;             
        end
    end
endmodule