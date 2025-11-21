/*
Summary:

- Four states: IDLE, READING_BUS_OP_ADDR, READING_BUS_DATA, TRANSFER_DATA_FSM_TO_BUS
    - In IDLE, wait for bus_valid and out_bus_ready to be high to start reading command
    - In READING_BUS_OP_ADDR, read 4 beats from the bus to get the command
        - First beat: enc/dec, reserved, dest, source, opcode
        - Next 3 beats: address (24 bits)
        - Depending on opcode, transition to READING_BUS_DATA or TRANSFER_DATA_FSM_TO_BUS
    - In READING_BUS_DATA, read data from bus and send to FSM
        - For WR_RES, read 16 or 32 beats depending on source (AES or SHA)
        - After reading all data, transition back to IDLE and send ack to accelerator
    - In TRANSFER_DATA_FSM_TO_BUS, read data from FSM and send to bus
        - For RD_KEY or RD_TEXT, read 32 or 16 beats depending on opcode
        - After reading all data, transition back to IDLE and send ack to controller

- Ack states: IDLE, RECEIVE_ACK, SEND_ACK_ACCEL, SEND_ACK_CTRL
    - RECEIVE_ACK state entered to receive ack from accelerator after RD_KEY or RD_TEXT done
    - SEND_ACK_ACCEL state entered to send ack to accelerator after WR_RES done
    - SEND_ACK_CTRL state entered to send ack to controller after either receiving ack from 
        accelerator from RECEIVE_ACK or after receiving address from the READING_BUS_OP_ADDR state
    
- Not sure about the ack bus, but I made the following assumptions:
    - ack_bus_owned indicates which module is driving the ack bus
    - ack_bus_request represents the ack value
    - ack_bus_id indicates which module is being sent the ack

- Uses r_w and ena signals to indicate read/write (or nothing)
- Always keeps fsm_ena, qspi_ena, status_ena high
- Uses a signal txn_done from FSM to indicate when a transaction is complete
- For the bi-directional 8-bit buses, input wire [7:0], output reg [7:0], and 
    input wire drive_bus / ouput wire drive_fsm_bus signals are used to control direction
- out_bus_ready driven by txn_done and fsm_ready
- out_fsm_ready driven by bus_ready

*/

module host_cmd_port_v2(
    input wire clk,
    input wire rst_n,

    // --- Bus ---
    input wire bus_valid,
    input wire bus_ready,
    input wire drive_bus, // CMD port can drive the bus when drive_bus is high
    input wire [7:0] in_bus_data,
    output reg [7:0] out_bus_data,
    output reg out_bus_ready,
    output reg out_bus_valid,
    
    // --- Ack Bus ---
    input wire ack_bus_owned,
    output reg ack_bus_request,
    output reg [1:0] ack_bus_id,

    // Not needed, but still an input from the status module
    input wire[6:0] status,

    // --- Transaction FSM ---
    input wire txn_done,
    input wire fsm_ready,
    input wire fsm_valid,
    output reg drive_fsm_bus, // CMD port can drive the FSM bus when drive_fsm_bus is high
    input wire [7:0] in_fsm_bus_data,
    output reg out_fsm_ready,
    
    // data buffered for fsm
    output reg [255:0] out_fsm_data,
    output reg out_fsm_valid,

    // --- outputs ---
    output reg r_w, // 1 for read, 0 for write
    output reg ena, // This is for enabling r_w (should be 0 if we're not reading or writing)
    output reg ena_fsm,
    output reg ena_qspi,
    output reg ena_status,

    // --- Length: goes to status module ---
    output reg length_valid,
    output reg [8:0] length,
    
    // --- Address: goes to qspi ---
    output reg address_valid,
    output reg[23:0] address
);

    // States
    localparam IDLE = 2'b00,
               READING_BUS_OP_ADDR = 2'b01,
               READING_BUS_DATA = 2'b10,
               TRANSFER_DATA_FSM_TO_BUS = 2'b11;

    // Ack states (Also reuses the IDLE state value)
    localparam RECEIVE_ACK = 2'b01,
               SEND_ACK_ACCEL = 2'b10,
               SEND_ACK_CTRL = 2'b11;

    // Opcodes
    localparam RD_KEY = 0,
               RD_TEXT = 1,
               WR_RES = 2,
               HASH_OP = 3;

    // Module IDs
    localparam MEM = 2'b00,
               SHA = 2'b01,
               AES = 2'b10,
               CTRL = 2'b11;

    // Internal registers for states and current beat
    reg [1:0] state;
    reg [1:0] ack_state;
    reg [5:0] cur_beat;

    // Opcode information
    reg enc_dec;
    reg reserved;
    reg [1:0] dest;
    reg [1:0] source;
    reg [1:0] noc_opcode;

    // FSM sequential logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset bus outputs
            out_bus_data <= 8'd0;
            out_bus_ready <= 1'b0;
            out_bus_valid <= 1'b0;

            // Reset FSM bus outputs
            out_fsm_data <= 256'd0;
            out_fsm_ready <= 1'b0;
            out_fsm_valid <= 1'b0;

            // Reset r_w and ena
            r_w <= 1'b0;
            ena <= 1'b0;
            ena_fsm <= 1'b0;
            ena_qspi <= 1'b0;
            ena_status <= 1'b0;

            // Reset length
            length_valid <= 1'b0;
            length <= 9'd0;

            // Reset address
            address_valid <= 1'b0;
            address <= 24'd0;

            // Reset states and beat
            state <= IDLE;
            ack_state <= IDLE;
            cur_beat <= 6'b000000;
            
            // Clear opcode information registers
            dest <= 2'b00;
            source <= 2'b00;
            noc_opcode <= 2'b00;
            
            // Enable all modules
            ena_fsm <= 1'b1;
            ena_qspi <= 1'b1;
            ena_status <= 1'b1;
            
            drive_fsm_bus <= 1'b0; // Default to not driving the FSM bus

            ack_bus_id <= 2'b00;
            ack_bus_request <= 1'b0;
        end
        else begin
            // Set the ready signals
            out_bus_ready <= txn_done;
            out_fsm_ready <= bus_ready;

            case (state)
                IDLE:
                    drive_fsm_bus <= 1'b0; // Default to not driving the FSM bus

                    // Polling: Get the next command from NOC if transaction done and if it is valid and fsm bus is ready
                    if (bus_valid && out_bus_ready) begin
                        state <= READING_BUS_OP_ADDR;
                        cur_beat <= 6'b000000;

                        // Reset the validity of length, address, and data
                        length_valid <= 1'b0;
                        address_valid <= 1'b0;
                        out_fsm_valid <= 1'b0;
                    end

                READING_BUS_OP_ADDR:
                    drive_fsm_bus <= 1'b0; // Default to not driving the FSM bus
                    length_valid <= 1'b0;
                    address_valid <= 1'b0;
                    
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
                                    cur_beat <= 6'b000001;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b01: begin
                                    // 1st beat: address
                                    address[7:0] <= in_bus_data[7:0];
                                    cur_beat <= 6'b000010;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b10: begin
                                    // 2nd beat: address
                                    address[15:8] <= in_bus_data[7:0];
                                    cur_beat <= 6'b000011;
                                    out_bus_ready <= 1'b1;
                                end
                                2'b11: begin
                                    // 3rd beat: address
                                    address[23:16] <= in_bus_data[7:0];
                                    address_valid <= 1'b1;
                                    cur_beat <= 6'b000000;
                                    ack_state <= SEND_ACK_CTRL;

                                    // If WR_RES, immediately send values to FSM
                                    // Otherwise, read the data from the bus
                                    if (noc_opcode == WR_RES) begin
                                        state <= READING_BUS_DATA;
                                        r_w <= 1'b0; // Writing to FSM
                                        ena <= 1'b1;
                                        length <=   (source == SHA) ? 256 :
                                                    (source == AES) ? 128 :
                                                                        0;
                                        length_valid <= 1; 
                                    end
                                    if (noc_opcode == RD_KEY) begin
                                        state <= TRANSFER_DATA_FSM_TO_BUS;
                                        length <= 9'd32; // 256 bits / 8 bits per beat = 32 beats
                                        length_valid <= 1'b1;
                                        r_w <= 1'b1; // Reading from FSM
                                        ena <= 1'b1;
                                    end
                                    else if (noc_opcode == RD_TEXT) begin
                                        state <= TRANSFER_DATA_FSM_TO_BUS;
                                        length <= (source == SHA) ? 9'32 : (source == AES) ? 9'd16 : 0; // 128 bits / 8 bits per beat = 16 beats
                                        length_valid <= 1'b1;
                                        r_w <= 1'b1; // Reading from FSM
                                        ena <= 1'b1;
                                    end
                                    else begin
                                        // This is HASH_OP, go back to IDLE because it does not concern MEM
                                        state <= IDLE;
                                        ena <= 1'b0;
                                    end
                                end
                            endcase
                        end
                    end

                READING_BUS_DATA:
                    // Not transmitting data through the fms bus
                    drive_fsm_bus <= 1'b0;

                    // drive_bus should be low since the cmd port is reading from the bus
                    if (drive_bus == 1'b1) begin
                        // Error: trying to read while driving the bus
                    end
                    else begin
                        // SHA involves reading 256 bits from the bus (256 bits / 8 bits per beat = 32 beats)
                        // AES involves reading 128 bits from the bus (128 bits / 8 bits per beat = 16 beats)
                        if ((source == SHA && cur_beat >= 32) || (source == AES && cur_beat >= 16)) begin
                            state <= IDLE;
                            cur_beat <= 6'b000000;
                            out_bus_ready <= 1'b0;
                            out_fsm_valid <= 1'b1;
                            length <=   (source == SHA) ? 256 :
                                        (source == AES) ? 128 :
                                                            0;
                            length_valid <= 1; 
                            ack_state <= SEND_ACK_ACCEL;
                        end
                        else if (bus_valid && out_bus_ready) begin
                            // Read the data (Assume that the first beat is the most significant byte)
                            out_fsm_data <= (out_fsm_data << 8) | in_bus_data;
                            cur_beat <= cur_beat + 1;
                            out_fsm_valid <= 1'b0;
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
                            cur_beat <= 6'b000000;
                            out_fsm_ready <= 1'b0;
                            out_bus_valid <= 1'b0;
                            ack_state <= RECEIVE_ACK;
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
                    if (ack_bus_owned) begin
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
                    if (!ack_bus_owned) begin
                        // Error: bus owned by memory controller when expecting ack from accelerator
                    end
                    else begin
                        // Send ack to accelerator after transaction done
                        if (txn_done) begin
                            ack_bus_request <= 1'b1;
                            ack_bus_id <= source; // Source is the accelerator ID
                            ack_state <= IDLE;
                        end
                    end
                
                SEND_ACK_CTRL:
                    // Assert that ack_bus_owned is memory
                    if (!ack_bus_owned) begin
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
