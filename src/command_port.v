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

Notes:
- Read source ID and set a flag if it is SHA or AES

*/

module host_cmd_port(
    input wire clk,
    input wire rst_n,

    // --- NoC / Control ---
    input wire bus_valid,
    input wire bus_ready,
    input wire drive_bus, // CMD port can drive the bus when drive_bus is high
    input wire [7:0] in_bus_data,
    output reg [7:0] out_bus_data,
    output reg out_bus_ready,
    output reg out_bus_valid,
    
    output reg cmd_ack,  // Ack when command done

    input wire ack_bus_owned,
    output wire ack_bus_request,
    output wire [1:0] ack_bus_id,

    // Not needed
    input wire[6:0] status,

    // --- Transaction FSM ---
    input wire txn_done,
    input wire fsm_ready,
    input wire fsm_valid,
    output wire drive_fsm_bus, // CMD port can drive the FSM bus when drive_fsm_bus is high
    input wire [7:0] in_fsm_bus_data,
    output reg [7:0] out_fsm_bus_data,
    output reg out_fsm_ready,
    output reg out_fsm_valid,

    // --- output ---
    output wire r_w,
    output reg ena_fsm,
    output reg ena_qspi,
    output reg ena_status,

    output reg [8:0] length,
    

    output wire address_valid,
    output reg[23:0] address,

    output wire data_valid,
    
    // --- QSPI controller ---
    output wire cmd_to_qspi_valid;
);

    localparam IDLE = 2'b00,
               READING_BUS_OP_ADDR = 2'b01,
               TRANSFER_DATA_BUS_TO_FSM = 2'b10,
               TRANSFER_DATA_FSM_TO_BUS = 2'b11;

    localparam RECEIVE_ACK = 2'b01,
               SEND_ACK_ACCEL = 2'b10,
               SEND_ACK_CTRL = 2'b11;

    localparam RD_KEY = 0,
               RD_TEXT = 1,
               WR_RES = 2,
               HASH_OP = 3;

    localparam MEM = 2'b00,
               SHA = 2'b01,
               AES = 2'b10,
               CTRL = 2'b11;

    reg [1:0] state;
    reg [1:0] ack_state;

    reg [5:0] cur_beat;
    reg [23:0] address;

    wire enc_dec;
    wire reserved;
    reg [1:0] dest;
    reg [1:0] source;
    reg [1:0] noc_opcode;

    // FSM sequential logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            cur_beat <= 2'b00;
            address <= 24'd0;
            address_valid <= 1'b0;
            data <= 129'd0;
            data_valid <= 1'b0;
            prev_bus_valid <= 1'b0;
            
            ena_fsm <= 1'b1;
            ena_qspi <= 1'b1;
            ena_status <= 1'b1;

            drive_bus <= 1'b0;

        end else begin
            // Set ack to 1 if the transaction is complete from FSM (Polling)
            if (txn_done) begin
                cmd_ack <= 1'b1;
            end
            else begin
                cmd_ack <= 1'b0;
            end

            // Relay the ready signal from FSM to bus
            out_bus_ready <= fsm_ready;
            out_fsm_ready <= bus_ready;

            case (state)
                IDLE:
                    // Polling: Get the next command from NOC if it is valid and if not busy
                    if (bus_valid && out_bus_ready) begin
                        state <= READING_BUS_OP_ADDR;
                        cur_beat <= 2'b00;
                    end

                READING_BUS_OP_ADDR:
                    // drive_bus should be low since the cmd port is reading from the bus
                    if (drive_bus == 1'b1) begin
                        // Error: trying to read while driving the bus
                    end
                    else begin
                        // Do I need !prev_bus_valid? ie. am I reading on a rising edge of bus_valid?
                        if (bus_valid && out_bus_ready) begin
                            case (cur_beat)
                                2'b00: begin
                                    // 0th beat: enc/dec, reserved, dest, source, opcode
                                    enc_dec <= in_bus_data[7];
                                    reserved <= in_bus_data[6];
                                    dest <= in_bus_data[5:4];
                                    source <= in_bus_data[3:2];
                                    noc_opcode <= in_bus_data[1:0];
                                    cur_beat <= 2'b01;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b01: begin
                                    // 1st beat: address
                                    address[7:0] <= in_bus_data[7:0];
                                    cur_beat <= 2'b10;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b10: begin
                                    // 2nd beat: address
                                    address[15:8] <= in_bus_data[7:0];
                                    cur_beat <= 2'b11;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b11: begin
                                    // 3rd beat: address
                                    address[23:16] <= in_bus_data[7:0];
                                    cur_beat <= 2'b00;
                                    ack_state <= SEND_ACK_CTRL

                                    // If WR_RES, immediately send values to FSM
                                    // Otherwise, read the data from the bus
                                    if (noc_opcode == WR_RES) begin
                                        state <= TRANSFER_DATA_BUS_TO_FSM;
                                    end
                                    if (noc_opcode == RD_KEY) begin
                                        state <= TRANSFER_DATA_FSM_TO_BUS;
                                        length <= 9'd32; // 256 bits / 8 bits per beat = 32 beats
                                    end
                                    else if (noc_opcode == RD_TEXT) begin
                                        state <= TRANSFER_DATA_FSM_TO_BUS;
                                        length <= 9'd16; // 128 bits / 8 bits per beat = 16 beats
                                    end
                                    else begin
                                        // This is HASH_OP, go back to IDLE because it does not concern MEM
                                        state <= IDLE;
                                    end
                                end
                            endcase
                        end
                    end
                    else begin
                        // Set the ready signal low if not reading
                        out_bus_ready <= 1'b0;
                    end

                TRANSFER_DATA_BUS_TO_FSM:
                    // Set the cmd port to drive the FSM bus
                    drive_fsm_bus <= 1'b1;

                    // drive_bus should be low since the cmd port is reading from the bus
                    if (drive_bus == 1'b1) begin
                        // Error: trying to read while driving the bus
                    end
                    else begin
                        if (bus_valid && out_bus_ready) begin
                            // Read the data
                            out_fsm_bus_data <= in_bus_data;
                            cur_beat <= cur_beat + 1;
                            out_fsm_valid <= 1'b1;
                        end
                        // SHA involves reading 256 bits from the bus (256 bits / 8 bits per beat = 32 beats)
                        // AES involves reading 128 bits from the bus (128 bits / 8 bits per beat = 16 beats)
                        if ((source == SHA && cur_beat >= 32) || (source == AES && cur_beat >= 16)) begin
                            state <= IDLE;
                            cur_beat <= 2'b00;
                            out_bus_ready <= 1'b0;
                            out_fsm_valid <= 1'b0;
                            ack_state <= SEND_ACK_ACCEL;
                        end
                    end

                TRANSFER_DATA_FSM_TO_BUS:
                    // Set the fsm to drive the FSM bus since cmd port is reading from FSM
                    drive_fsm_bus <= 1'b0;

                    // drive_bus should be high since the cmd port is writing to the bus
                    if (drive_bus == 1'b0) begin
                        // Error: trying to write to the bus but not driving the bus
                    end
                    else begin
                        if (fsm_valid && out_fsm_ready) begin
                            // Read the data
                            out_bus_data <= in_fsm_bus_data;
                            cur_beat <= cur_beat + 1;
                            out_bus_valid <= 1'b1;
                        end

                        // RD_KEY involves reading 256 bits from the bus (256 bits / 8 bits per beat = 32 beats)
                        // RD_TEXT involves reading 128 bits from the bus (128 bits / 8 bits per beat = 16 beats)
                        if ((noc_opcode == RD_KEY && cur_beat >= 32) || (noc_opcode == RD_TEXT && cur_beat >= 16)) begin
                            state <= IDLE;
                            cur_beat <= 2'b00;
                            out_fsm_ready <= 1'b0;
                            out_bus_valid <= 1'b0;
                            state <= RECEIVE_ACK;
                        end
                    end
            endcase

            // Ack bus state machine (referenced from the diagram in https://docs.uwasic.com/doc/architecture-document-l9c2Skeheb)
            case (ack_state)
                IDLE:
                    // Do nothing
                
                RECEIVE_ACK:
                    // Wait for ack from ack bus from accelerator
                    // Assert that ack_bus_owned is not memory
                    if (ack_bus_owned == MEM) begin
                        // Error: bus owned by memory controller when expecting ack from accelerator
                        ack_bus_request <= 1'b0;
                    end
                    else begin
                        // Not sure if this is the correct implementation
                        // If ack was intended to be sent to MEM and ack has been sent
                        if (ack_bus_id == MEM && ack_bus_request == 1) begin
                            // We accepted the ack from accelerator. Now send ack to controller
                            ack_state <= SEND_ACK_CTRL;
                        end
                    end
                
                SEND_ACK_ACCEL:
                    // Assert that ack_bus_owned is memory
                    if (ack_bus_owned != MEM) begin
                        // Error: bus owned by memory controller when expecting ack from accelerator
                    end
                    else begin
                        // Send ack to accelerator after receiving data from bus
                        ack_bus_request <= 1'b1;
                        ack_bus_id <= source; // Source is the accelerator ID
                        ack_state <= IDLE;
                    end
                
                SEND_ACK_CTRL:
                    // Assert that ack_bus_owned is memory
                    if (ack_bus_owned != MEM) begin
                        // Error: bus owned by memory controller when expecting ack from accelerator
                    end
                    else begin
                        // Send ack to control after receiving address
                        ack_bus_request <= 1'b1;
                        ack_bus_id <= CTRL;
                        ack_state <= IDLE;
                    end
            endcase
        end
    end

endmodule
