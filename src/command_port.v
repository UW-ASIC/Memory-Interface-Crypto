/*
Questions:
- What is in the opcode [1:0] from the NOC?
- Purpose of source and dest from NOC? Should they be written to somewhere or are they just used for decoding r_w, RD_KEY, RD_TEXT, WR_RES?
- How should r_w, ena, RD_KEY, RD_TEXT, WR_RES be decoded?
- WHat is the data being written to FSM and QSPI?
- Where should cmd port send the address?
- From Network-on_chip What is your data??????? :
    "Data sent:
        256 bit key
        128 bit text"
    Does this mean that the cmd port should handle reading the data from the bus as well?
*/

module host_cmd_port #(
    parameter OPCODE_WIDTH = 4,
    parameter LEN_WIDTH    = 8
)(
    input  wire              clk,
    input  wire              rst_n,

    // --- NoC / Control ---
    input  wire              noc_valid,
    input  wire [7:0]        noc_data,
    output reg               out_noc_ready,
    output reg               cmd_ack,  // Ack when command done

    // --- Status Poller ---
    input  wire              poll_done,
    input  wire              we_flag,
    input  wire              qe_flag,
    input  wire              busy_flag,

    // --- Transaction FSM ---
    input  wire              txn_done,
    input  wire              fsm_ready,

    // --- Transaction FSM / Status Poller ---
    output reg  [OPCODE_WIDTH-1:0] opcode,
    output reg  [LEN_WIDTH-1:0]    length,
    output wire cmd_to_fsm_valid,

    // --- output ---
    output wire r_w,
    output wire ena,

    // --- QSPI controller ---
    output reg[7:0] address,
    output wire cmd_to_qspi_valid;
);

    localparam IDLE = 2'b00,
               READING_NOC = 2'b01,
               READING_FSM = 2'b10,
               WRITING_NOC = 2'b11,
               WRITING_FSM = 3'b100;

    reg wire state;
    reg [1:0] cur_beat;
    reg [23:0] address;

    wire enc_dec;
    wire reserved;
    wire [1:0] dest;
    wire [1:0] source;
    wire [1:0] noc_opcode;

    reg RD_KEY, RD_TEXT, WR_RES;

    reg [23:0] data_to_write;

    // FSM sequential logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
            cur_beat <= 2'b00;
            address <= 24'd0;
            RD_KEY <= 1'b0;
            RD_TEXT <= 1'b0;
            WR_RES <= 1'b0;
        else
            // Set ack to 1 if the transaction is complete from FSM (Polling)
            if (txn_done) begin
                cmd_ack <= 1'b1;
            end
            else begin
                cmd_ack <= 1'b0;
            end

            case (state)
                IDLE:
                    // Polling: Get the next command from NOC if it is valid and if not busy
                    if (noc_valid && !busy_flag) begin
                        state <= READING_NOC;
                        cur_beat <= 2'b00;
                    end 
                    else if (RD_KEY || RD_TEXT) begin
                        // poll FSM data ready, whenever data is ready present data on the bus 8 bits at a time and assert valid for 1 cycle
                        if (fsm_ready) begin
                            state <= WRITING_FSM;
                            data <= 
                            cur_beat <= 2'b00;
                        end
                    end
                    else if (WR_RES) begin
                        // WRITE RES over N(tbd) bytes to the FSM whenever Transaction FSM is ready to receive
                        state <= WRITING_FSM;
                        cur_beat <= 2'b00;
                    end
                READING_NOC:
                    if (noc_valid && !busy_flag) begin
                        case (cur_beat)
                            2'b00: begin
                                // 0th beat: enc/dec, reserved, dest, source, opcode
                                enc_dec       <= noc_data[7];
                                reserved      <= noc_data[6];
                                dest         <= noc_data[5:4];
                                source      <= noc_data[3:2];
                                noc_opcode  <= noc_data[1:0];
                                cur_beat    <= 2'b01;
                                out_noc_ready <= 1'b1;

                                // Decode RD_KEY, RD_TEXT, WR_RES (based on noc_opcode?)
                                // Should I also be setting r_w and ena here?
                                case (noc_opcode)
                                    2'b00: 
                                        RD_KEY <= 1'b1; // Read Key
                                        RD_TEXT <= 1'b1; // Read Text
                                        WR_RES <= 1'b1; // Write Result
                                    2'b01:
                                        RD_KEY <= 1'b1; // Read Key
                                        RD_TEXT <= 1'b1; // Read Text
                                        WR_RES <= 1'b1; // Write Result
                                    2'b10:
                                        RD_KEY <= 1'b1; // Read Key
                                        RD_TEXT <= 1'b1; // Read Text
                                        WR_RES <= 1'b1; // Write Result
                                endcase
                            end
                            2'b01: begin
                                // 1st beat: address
                                address[7:0] <= noc_data[7:0];
                                cur_beat    <= 2'b10;
                                out_noc_ready <= 1'b1;
                            end
                            2'b10: begin
                                // 2nd beat: address
                                address[15:8] <= noc_data[7:0];
                                cur_beat    <= 2'b11;
                                out_noc_ready <= 1'b1;
                            end
                            2'b11: begin
                                // 3rd beat: address
                                address[23:16] <= noc_data[7:0];
                                cur_beat    <= 2'b00;
                                out_noc_ready <= 1'b1;
                                state <= WRITING_FSM;
                            end

                        endcase
                    end
                    else begin
                        // Set the ready signal low if not reading
                        out_noc_ready <= 1'b0;
                        cur_beat <= 2'b00;
                    end

                READING_FSM:
                    // Is there anything that the cmd port should read from FSM through the bus?
                SENDING_FSM:
                    // Send the r_w and ena data
                    if (fsm_ready) begin
                        case (cur_beat)
                            2'b00: begin
                                // Send first 8 bits
                                cur_beat <= 2'b01;
                            end
                            2'b01: begin
                                // Send second 8 bits
                                cur_beat <= 2'b10;
                            end
                            2'b10: begin
                                // Send third 8 bits
                                cur_beat <= 2'b11;
                            end
                            2'b11: begin
                                // Send last 8 bits
                                cur_beat <= 2'b00;
                                state <= IDLE;
                            end
                        endcase
                    end
                WRITING_NOC:
            endcase
    end

endmodule
