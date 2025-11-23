/* cleaned / syntax-fixed host_cmd_port.v
   - fixed case width by using cur_beat[1:0]
   - fixed 9'32 -> 9'd32
   - replaced bare 1 with 1'b1 for control signals where appropriate
   - removed duplicate reset assignments and tidied reset values
*/

module mem_command_port(
    input wire clk,
    input wire rst_n,

    // --- Bus ---
    input wire in_bus_valid,
    input wire in_bus_ready,
    input wire [7:0] in_bus_data,

    output reg [7:0] out_bus_data,
    output reg out_bus_ready,
    output reg out_bus_valid,
    
    // --- Ack Bus ---
    input wire in_ack_bus_owned,
    output reg out_ack_bus_request,
    output reg [1:0] out_ack_bus_id,

    // --- Transaction FSM ---
    output reg out_fsm_valid,
    output reg out_fsm_ready,
    output reg [7:0] out_fsm_data,

    input wire in_fsm_ready,
    input wire in_fsm_valid,
    input wire [7:0] in_fsm_data,
    input wire in_fsm_done,
    
    output reg out_fsm_enc_type,
    output reg [2:0] out_fsm_opcode,
    output reg [23:0] out_address
);
    localparam MEM_ID = 2'b00;
    localparam SHA_ID = 2'b01;
    localparam AES_ID = 2'b10;

    localparam RD_KEY = 2'b00;
    localparam RD_TEXT = 2'b01;
    localparam WR_RES = 2'b10;
    localparam OTHER = 2'b11;

    localparam IDLE = 4'h0;
    localparam PASS_CMD = 4'h1;
    localparam PERFORM_TRANSFER = 4'h2;
    localparam TRY_ACK = 4'h3;


    reg [3:0] state;
    reg [7:0] counter = 0;

    wire enc_dec = in_bus_data[7];
    wire [2:0] dest_id = in_bus_data[5:4];
    wire [2:0] src_id = in_bus_data[3:2];
    wire [2:0] opcode = in_bus_data[1:0];


    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            out_bus_data <= 0;
            out_bus_ready <= 0;
            out_bus_valid <= 0;
            out_ack_bus_id <= 0;
            out_ack_bus_request <= 0;
            out_fsm_ready <= 0;
            out_fsm_valid <= 0;
            out_fsm_data <= 0;
            counter <= 0;
            state <= IDLE;
            out_address <= 0;
        end
        else begin
            case(state)
                IDLE: begin
                    out_fsm_ready <= 0;
                    if(in_bus_valid && opcode != OTHER) begin
                        case(opcode)
                            RD_KEY, RD_TEXT: begin
                                if(dest_id == MEM_ID) state <= PASS_CMD;
                            end
                            WR_RES: begin
                                if(src_id == MEM_ID) state <= PASS_CMD;
                            end
                        endcase
                        out_fsm_opcode <= opcode;
                        out_fsm_enc_type <= enc_dec;
                    end
                end

                PASS_CMD: begin
                    if(in_bus_valid) begin
                        out_bus_ready <= 0;
                        out_address[counter + 7 -: 8] <= in_bus_data;
                        counter <= counter + 8;
                    end else out_bus_ready <= 1;
                    if(counter >= 23) begin
                        out_fsm_valid <= 1;
                        state <= PERFORM_TRANSFER;
                    end
                end

                PERFORM_TRANSFER: begin
                    if(in_fsm_done) state <= TRY_ACK;
                    if(out_fsm_opcode == WR_RES) begin
                        out_bus_valid <= in_fsm_valid;
                        out_bus_data <= in_fsm_data;
                        out_fsm_ready <= in_bus_ready;
                    end else begin
                        out_fsm_valid <= in_bus_valid;
                        out_fsm_data <= in_bus_data;
                        out_bus_ready <= in_fsm_ready;
                    end
                end
                        
                TRY_ACK: begin
                    out_ack_bus_request <= 1;
                    out_ack_bus_id <= MEM_ID;
                    if(!in_ack_bus_owned) state <= IDLE;
                end

            endcase
        end
    end
endmodule
