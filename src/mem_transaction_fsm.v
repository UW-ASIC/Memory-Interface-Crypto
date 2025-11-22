module mem_transaction_fsm(
    input wire clk,
    input wire rst_n,

    //command port
    input wire in_cmd_valid,
    input wire in_cmd_enc_type,
    input wire [1:0] in_cmd_opcode,
    input wire [23:0] in_cmd_addr,
    output reg out_fsm_cmd_ready,

    //write data from cmd
    input wire in_wr_data_valid,
    input wire [7:0] in_cmd_data,
    output reg out_fsm_data_ready,

    //read data back to cmd
    output reg out_wr_cp_data_valid,
    output reg [7:0] out_wr_cp_data,
    input wire in_wr_cp_ready,

    //SPI controller ctrl
    output reg out_spi_start,
    output reg [15:0] out_spi_num_bytes,
    input wire in_spi_busy,
    input wire in_spi_done,

    //data to SPI controller
    output reg out_spi_tx_valid,
    output reg [7:0] out_spi_tx_data,
    input wire in_spi_tx_ready,

    //data from SPI controller
    input wire in_spi_rx_valid,
    input wire [7:0] in_spi_rx_data,
    output reg out_spi_rx_ready,

    output reg out_spi_r_w,     //1=read,0=write (to qspi)
    output reg out_spi_dummy,   //1=qspi hold / send dummy clocks

    //to status
    output reg out_byte_done,      //pulse: 1 real data byte done
    output reg out_status_we,      //status[6]
    output reg out_status_qe,      //status[5]
    output reg [1:0] out_status_mode, //status[3:2]
    output reg out_swdo_start,     //kick short watchdog
    output reg out_lwdo_start,     //kick long watchdog
    output reg out_gwdo_start,     //kick global watchdog
    input wire in_status_op_done   //status counter says: reached length

);
    // Dump the signals to a VCD file. You can view it with gtkwave or surfer.
    initial begin
        $dumpfile("mem_transaction_fsm.vcd");
        $dumpvars(0, mem_transaction_fsm);
        #1;
    end

    //flash opcodes
    localparam [7:0] OPC_ENABLE_RESET = 8'h66;
    localparam [7:0] OPC_RESET = 8'h99;
    localparam [7:0] OPC_WREN = 8'h06;
    localparam [7:0] OPC_GLOBAL_UNLOCK = 8'h98;
    localparam [7:0] OPC_QE = 8'h31;
    localparam [7:0] FLASH_READ = 8'h6B; //fast read quad output (needs dummy)
    localparam [7:0] FLASH_PP = 8'h32; //quad input page program (no dummy)
    localparam [7:0] FLASH_SE = 8'h20;
    localparam [7:0] FLASH_RDSR = 8'h05;

    //states
    localparam S_BOOT_ENA = 5'd0;
    localparam S_BOOT_ENA_WAIT = 5'd1;
    localparam S_BOOT_RST = 5'd2;
    localparam S_BOOT_RST_WAIT = 5'd3;
    localparam S_BOOT_WREN = 5'd4;
    localparam S_BOOT_WREN_WAIT = 5'd5;
    localparam S_BOOT_GULK = 5'd6;
    localparam S_BOOT_GULK_WAIT = 5'd7;

    localparam S_IDLE = 5'd8;
    localparam S_LOAD_CMD = 5'd9;
    localparam S_PRE_WREN = 5'd10;
    localparam S_PRE_WREN_WAIT = 5'd11;
    localparam S_START_SPI = 5'd12;
    localparam S_SEND_CMD = 5'd13;
    localparam S_SEND_A2 = 5'd14;
    localparam S_SEND_A1 = 5'd15;
    localparam S_SEND_A0 = 5'd16;
    localparam S_SEND_DUMMY = 5'd17;
    localparam S_SEND_WDATA = 5'd18;
    localparam S_RECV_DATA = 5'd19;
    localparam S_WAIT_DONE = 5'd20;
    localparam S_FINISH = 5'd21;

    localparam S_SEND_QE = 5'd22;

    localparam RD_KEY = 2'b00;
    localparam RD_TEXT = 2'b01;
    localparam WR_RES = 2'b10;

    reg [4:0] state;
    reg [4:0] next_state;

    reg [3:0] rst_wait;
    wire [3:0] t_rst = 4;
    reg [3:0] gp_counter;

    reg status_qe;

    //latched command
    reg [1:0] opcode_q;
    reg [23:0] addr_q;
    reg [7:0] flash_cmd_byte;
    reg [15:0] total_bytes;
    reg [7:0] total_recv_bytes;
    reg need_dummy;
    reg need_pre_wren;

    //sequential
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_BOOT_ENA;
            opcode_q <= 2'b00;
            addr_q <= 24'h0;
            flash_cmd_byte <= 8'h00;
            total_bytes <= 16'd0;
            total_recv_bytes <= 16'd0;
            out_fsm_cmd_ready <= 1'b0;
            out_fsm_data_ready <= 1'b0;
            out_wr_cp_data_valid <= 1'b0;
            out_wr_cp_data <= 8'h00;
            out_spi_start <= 1'b0;
            out_spi_num_bytes <= 16'd0;
            out_spi_tx_valid <= 1'b0;
            out_spi_tx_data <= 8'h00;
            out_spi_rx_ready <= 1'b0;
            out_spi_r_w <= 1'b0;
            out_spi_dummy <= 1'b0;
            out_byte_done <= 1'b0;
            out_status_we <= 1'b0;
            out_status_qe <= 1'b0;
            out_status_mode <= 2'b11; //default to 4 IOs
            out_swdo_start <= 1'b0;
            out_lwdo_start <= 1'b0;
            out_gwdo_start <= 1'b0;
            need_dummy <= 1'b0;
            need_pre_wren <= 1'b0;

            status_qe <= 0;
            gp_counter <= 0;
            rst_wait <= 0;
        end else begin
        state <= next_state;

        //defaults
        out_fsm_cmd_ready <= 1'b0;
        out_fsm_data_ready <= 1'b0;
        out_wr_cp_data_valid <= 1'b0;
        out_spi_start <= 1'b0;
        out_spi_tx_valid <= 1'b0;
        out_spi_rx_ready <= 1'b0;
        out_spi_dummy <= 1'b0;
        out_byte_done <= 1'b0;
        out_swdo_start <= 1'b0;
        out_lwdo_start <= 1'b0;
        out_gwdo_start <= 1'b0;

            case(state)
                
                // -------- STARTUP FLOW --------
                S_BOOT_ENA: begin
                    //send 66h
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= 16'd1;
                    out_spi_tx_valid <= 1'b1;
                    out_spi_tx_data <= OPC_ENABLE_RESET;
                    out_spi_r_w <= 1'b0;
                end

                S_BOOT_ENA_WAIT: begin
                    //wait for spi done
                end

                S_BOOT_RST: begin
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= 16'd1;
                    out_spi_tx_valid <= 1'b1;
                    out_spi_tx_data <= OPC_RESET;
                    out_spi_r_w <= 1'b0;
                end

                S_BOOT_RST_WAIT: begin
                    //wait
                    if(rst_wait <= t_rst) rst_wait <= rst_wait + 1;
                end

                S_BOOT_WREN: begin
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= 16'd1;
                    out_spi_tx_valid <= 1'b1;
                    out_spi_tx_data <= OPC_WREN;
                    out_spi_r_w <= 1'b0;
                    out_status_we <= 1'b1; 
                end

                S_BOOT_WREN_WAIT: begin
                    //wait
                    //also wait for 10 clock cycles for tRST
                    // if(rst_wait <= t_rst) rst_wait <= rst_wait + 1;
                end

                S_BOOT_GULK: begin
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= 16'd1;
                    out_spi_tx_valid <= 1'b1;
                    out_spi_tx_data <= OPC_GLOBAL_UNLOCK;
                    out_spi_r_w <= 1'b0;
                end

                S_BOOT_GULK_WAIT: begin
                    //after this we go idle
                end

                // -------- NORMAL FLOW --------
                S_IDLE: begin
                    if(in_cmd_valid) begin
                        opcode_q <= in_cmd_opcode;
                        addr_q <= in_cmd_addr;
                        out_fsm_cmd_ready <= 1'b1;
                    end
                end

                S_LOAD_CMD: begin
                    case(opcode_q)
                        RD_KEY, RD_TEXT: begin //RD_KEY / RD_TEXT
                            flash_cmd_byte <= FLASH_READ;
                            total_bytes <= 16'd6; //cmd + 3 addr + dummy + 1 data (len is counted by status)
                            if(opcode_q == RD_KEY) total_recv_bytes <= 8'd32;
                            else begin
                                if(in_cmd_enc_type == 0) total_recv_bytes <= 8'd8;
                                else total_recv_bytes <= 8'd64;
                            end
                            need_dummy <= 1'b1;
                            need_pre_wren <= 1'b0;
                            out_spi_r_w <= 1'b1; //read
                        end
                        2'b10: begin //WR_RES
                            flash_cmd_byte <= FLASH_PP;
                            total_bytes <= 16'd5; //cmd + 3 addr + 1 data (len is counted by status)
                            need_dummy <= 1'b0;
                            need_pre_wren <= 1'b1; //WREN before PP
                            out_spi_r_w <= 1'b0; //write
                        end
                        default: begin
                            flash_cmd_byte <= FLASH_RDSR;
                            total_bytes <= 16'd2; //cmd + 1 data
                            need_dummy <= 1'b0;
                            need_pre_wren <= 1'b0;
                            out_spi_r_w <= 1'b1;
                        end
                    endcase

                    //kick timers for a new op
                    out_swdo_start <= 1'b1;
                    out_lwdo_start <= 1'b1;
                    out_gwdo_start <= 1'b1;
                end

                //optional per-op write enable
                S_PRE_WREN: begin
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= 16'd1;
                    out_spi_tx_valid <= 1'b1;
                    out_spi_tx_data <= OPC_WREN;
                    out_spi_r_w <= 1'b0;
                    out_status_we <= 1'b1;
                    rst_wait <= 0;
                end

                S_PRE_WREN_WAIT: begin
                    //wait for spi_done
                end

                S_START_SPI: begin
                    out_spi_start <= 1'b1;
                    out_spi_num_bytes <= total_bytes;
                    gp_counter <= 0;
                end

                S_SEND_QE: begin
                    out_spi_tx_valid <= 1'b1;
                    if(gp_counter == 0) out_spi_tx_data <= OPC_QE;
                    else out_spi_tx_data <= 8'b00000010;
                    gp_counter <= gp_counter + 1;
                end    

                S_SEND_CMD: begin
                    if(in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= flash_cmd_byte;
                    end
                end

                S_SEND_A2: begin
                    if(in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= addr_q[23:16];
                    end
                end

                S_SEND_A1: begin
                    if(in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= addr_q[15:8];
                    end
                end

                S_SEND_A0: begin
                    if(in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= addr_q[7:0];
                    end
                end

                S_SEND_DUMMY: begin
                    if(in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= 8'h0;
                    end
                end

                S_SEND_WDATA: begin
                    out_fsm_data_ready <= 1'b1;

                    if(in_wr_data_valid && in_spi_tx_ready) begin
                        out_spi_tx_valid <= 1'b1;
                        out_spi_tx_data <= in_cmd_data;
                        out_byte_done <= 1'b1;
                    end
                end

                S_RECV_DATA: begin
                    out_spi_rx_ready <= 1'b1;
                    total_recv_bytes <= total_recv_bytes - 1;

                    if(in_spi_rx_valid) begin
                        out_wr_cp_data <= in_spi_rx_data;

                        if(in_wr_cp_ready) begin
                            out_wr_cp_data_valid <= 1'b1;
                        end
                        out_byte_done <= 1'b1;
                    end
                end

                S_WAIT_DONE: begin
                    //wait spi_done
                end

                S_FINISH: begin
                    //wait status counter done -> will hop to IDLE in comb
                end

                default: begin end
            endcase
        end
    end

    //next state logic
    always @(*) begin
        next_state = state;
        
        case(state)

            //startup chain
            S_BOOT_ENA: next_state = S_BOOT_ENA_WAIT;
            S_BOOT_ENA_WAIT: next_state = in_spi_done ? S_BOOT_RST : S_BOOT_ENA_WAIT;
            S_BOOT_RST: next_state = S_BOOT_RST_WAIT;
            S_BOOT_RST_WAIT: next_state = (in_spi_done && rst_wait >= t_rst) ? S_BOOT_WREN : S_BOOT_RST_WAIT;
            S_BOOT_WREN: next_state = S_BOOT_WREN_WAIT;
            S_BOOT_WREN_WAIT: next_state = in_spi_done ? S_BOOT_GULK : S_BOOT_WREN_WAIT;
            S_BOOT_GULK: next_state = S_BOOT_GULK_WAIT;
            S_BOOT_GULK_WAIT: next_state = in_spi_done ? S_IDLE : S_BOOT_GULK_WAIT;

            //normal flow
            S_IDLE: begin
                if(in_cmd_valid) begin
                    next_state = S_LOAD_CMD;
                end
            end

            S_LOAD_CMD: begin
                if(need_pre_wren) begin
                    next_state = S_PRE_WREN;
                end else begin
                    next_state = S_START_SPI;
                end
            end
            
            S_PRE_WREN: begin
                next_state = S_PRE_WREN_WAIT;
            end

            S_PRE_WREN_WAIT: begin
                if(in_spi_done) begin
                    next_state = S_START_SPI;
                end
            end

            S_START_SPI: begin
                next_state = S_SEND_CMD;
                if(!status_qe) next_state = S_SEND_QE;
            end

            S_SEND_QE: begin
                if(gp_counter >= 1) next_state = S_SEND_CMD;
            end

            S_SEND_CMD: begin
                if(in_spi_tx_ready) begin
                    if(opcode_q == 2'b11) begin
                        next_state = S_RECV_DATA; //RDSR
                    end else begin
                        next_state = S_SEND_A2;
                    end
                end
            end

            S_SEND_A2: begin
                if(in_spi_tx_ready) begin
                    next_state = S_SEND_A1;
                end
            end

            S_SEND_A1: begin
                if(in_spi_tx_ready) begin
                    next_state = S_SEND_A0;
                end
            end

            S_SEND_A0: begin
                if(in_spi_tx_ready) begin
                    if(need_dummy) begin
                        next_state = S_SEND_DUMMY;
                    end else if(opcode_q == RD_KEY || opcode_q == RD_TEXT) begin
                        next_state = S_RECV_DATA;
                    end else if(opcode_q == WR_RES) begin
                        next_state = S_SEND_WDATA;
                    end else begin
                        next_state = S_WAIT_DONE;
                    end
                end
            end

            S_SEND_DUMMY: begin
                //dummy is just 1 slot we tell qspi to insert
                if(opcode_q == RD_KEY || opcode_q == RD_TEXT) begin
                    next_state = S_RECV_DATA;
                end else if(opcode_q == 2'b10) begin
                    next_state = S_SEND_WDATA;
                end else begin
                    next_state = S_WAIT_DONE;
                end
            end

            S_SEND_WDATA: begin
                // if(in_wr_data_valid && in_spi_tx_ready) begin
                //     next_state = S_WAIT_DONE;
                // end
                if(in_status_op_done) begin
                    next_state = S_WAIT_DONE;
                end
            end

            S_RECV_DATA: begin
                if(total_recv_bytes == 0) begin
                    next_state = S_WAIT_DONE;
                end
            end

            S_WAIT_DONE: begin
                if(in_spi_done) begin
                    next_state = S_FINISH;
                end
            end

            S_FINISH: begin
                if(in_status_op_done) begin
                    next_state = S_IDLE;
                end
            end

            default: begin
                next_state = S_IDLE;
            end
        endcase
    end
endmodule
