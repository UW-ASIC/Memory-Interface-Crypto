module QSPI_controller (
    input clk,
    input rst_n,
    //---signals with transaction fsm----
    input [7:0] data_in, //input from fsm
    input r_w,
    output reg [7:0] data_out, //output to fsm
    input [1:0] width,
    input fsm_ready,
    input fsm_valid,
    output reg ctrl_valid,
    output reg ctrl_ready,
    //---signals with flash-----
    output reg [3:0] out, //to flash
    input [3:0] in, //input from flash
    output reg n_cs,
    output reg sck
);
// Dump the signals to a VCD file. You can view it with gtkwave or surfer.
initial begin 
    $dumpfile("module_name.vcd"); 
    $dumpvars(0, module_name); 
    #1; 
end

localparam WIREWIDTH_1 = 2'b00;
localparam WIREWIDTH_2 = 2'b01;
localparam WIREWIDTH_4 = 2'b10;
localparam DIVIDER = 1; //divider == 1 means half frequency, divider == 2 means quarter frequency 

reg sck_prev = 0;
reg sck_counter;
wire sck_rising;
wire sck_falling;

assign sck_rising = (sck == 1 && sck_prev == 0);
assign sck_falling = (sck == 0 && sck_prev == 1);
wire [4:0] num_cycles;
reg [4:0] cycle_count;
assign num_cycles = (width == WIREWIDTH_1) ? 4'b1000 : //standard spi: 8 cycles
                    (width == WIREWIDTH_2) ? 4'b0100 : //dual spi: 4 cycles
                                             4'b0010; //quad spi: 2 cycles
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
        ctrl_ready <= 1;
        internal_rw <= 0;
        n_cs <= 1;
    end else begin
        case(state)
            IDLE: begin
                ctrl_valid <= 0;
                ctrl_ready <= 1;
                n_cs <= 1;
                if(fsm_valid) begin
                    internal_data <= data_in;
                    internal_rw <= r_w;
                    ctrl_ready <= 0;
                    state <= BUSY;
                    n_cs <= 0;
                end
            end
            BUSY: begin
                ctrl_valid <= 0;
                ctrl_ready <= 0;
                n_cs <= 0;
                if(transaction_done) begin
                    ctrl_valid <= 1;
                    state <= FINISHED;
                    n_cs <= 1;
                end
            end
            FINISHED: begin
                ctrl_valid <= 1;
                ctrl_ready <= 0;
                n_cs <= 1;
                if(fsm_ready) begin
                    ctrl_valid <= 0;
                    ctrl_ready <= 1;
                    state <= IDLE;
                end
            end
            default: begin
                state <= IDLE;
                ctrl_ready <= 1;
                ctrl_valid <= 0;
                n_cs <= 1;
            end
        endcase
    end
end


//generate sck
always @ (posedge clk or negedge rst_n) begin
    if(!rst_n)begin
        sck <= 0;
        sck_prev <= 0;
        sck_counter <= 0;
    end else begin
        if(state == BUSY)begin
            sck_prev <= sck;
            if(sck_counter == DIVIDER - 1)begin
                sck <= ~sck;
                sck_counter <= 0;
            end else begin
                sck_counter <= sck_counter + 1;
            end
        end else begin
            sck <= 0;
            sck_counter <= 0;
            sck_prev <= 0;
        end
    end
end

//interact with flash
always @ (posedge clk or negedge rst_n) begin
    if(!rst_n)begin
        transaction_done <= 0;
        data_out <= 0;
        cycle_count <= 0;
    end else if(state == BUSY)begin 
        if(cycle_count == num_cycles - 1)begin
            transaction_done <= 1;
            cycle_count <= 0;
        end else begin
            cycle_count <= cycle_count + 1;
            transaction_done <= 0;
        end
        if(!internal_rw) begin //read on rising sclk edge
            if(sck_rising)begin
                case(width)
                    WIREWIDTH_1: begin
                        //read data one bit at a time
                        data_out <= {data_out[6:0], in[0]};
                    end
                    WIREWIDTH_2: begin
                        //read data 2 bits at a time
                        data_out <= {data_out[5:0], in[1:0]};
                    end
                    WIREWIDTH_4: begin
                        //read data 4 bits at a time
                        data_out <= {data_out[3:0], in[3:0]};
                    end
                endcase
            end
        end else begin //write on falling sclk edge
            if (sck_falling)begin
                case(width)
                    WIREWIDTH_1: begin
                        //shift out data one bit at a time
                        out[0] <= internal_data[cycle_count];
                    end
                    WIREWIDTH_2: begin
                        //shift out data 2 bits at a time
                        out[1:0] <= internal_data[cycle_count*2 +: 2];
                    end
                    WIREWIDTH_4: begin
                        //shift out data 4 bits at a time
                        out[3:0] <= internal_data[cycle_count*4 +: 4];
                    end
                endcase
            end
        end
    end else begin //idle or finished state
        transaction_done <= 0;
        cycle_count <= 0;
    end
end
endmodule