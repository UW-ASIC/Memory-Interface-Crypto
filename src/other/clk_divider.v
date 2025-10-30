module clk_divider #(
    parameter integer system_clk_freq = 100; //100mhz
    parameter integer DIV = 1; //25mhz

) (
    input wire clk, //system clock
    input wire rst_n, // async active low reset
    input wire ena,
    output reg sclk_tick, //serial clock max 50 mhz, mode 0
    output wire sclk_rise, // sclk rising edge
    output wire sclk_fall // sclk falling edge
);
    reg[$clog2(DIV+1) - 1:0] cnt;
    reg sclk, sclk_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 0;
            sclk_tick <= 0;
            sclk <= 0;
            sclk_d <= 0;
        end else if(ena) begin
            if (cnt == DIV) begin
                sclk_tick <= 1;
                cnt <= 0;
            end else begin
                cnt <= cnt + 1;
                sclk_tick <= 0;
            end    
        end else begin
            sclk_tick <= 0;
            cnt <= 0;
            sclk <= 0;
            sclk_d <= 0;          
        end
    end
    assign sclk_rise = (sclk & !sclk_d & sclk_tick);
    assign sclk_fall = (!sclk & sclk_d & sclk_tick);

endmodule