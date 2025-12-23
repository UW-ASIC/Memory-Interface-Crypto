// ASSUME CLK 100MHZ

`default_nettype none
module mem_txn_fsm(
    input wire clk,
    input wire rst_n,

    // CU
    output wire out_cu_ready,
    input wire in_cu_valid,
    input wire [7:0] in_cu_data,

    input wire in_cu_ready,
    output reg out_cu_valid,
    output reg [7:0] out_cu_data,

    output reg in_fsm_done, // spi side finished
    
    input wire out_fsm_enc_type,
    input wire [1:0] out_fsm_opcode,
    input wire [23:0] out_address,

    // QSPI

    //---- Transaction FSM connections ----
    output reg in_start, //start the transaction
    output reg r_w, //1 is read, 0 is write
    output reg quad_enable, //0 use standard, 1 use quad
    input wire in_spi_done, //tell the fsm we are done

    output reg qed, // tell spi its in standard spi mode drive uio oe [3:2] 11 and latch io [3:2] high

    //Send, MOSI side for write text commands
    output reg out_spi_valid, //the fsm data is valid
    output reg [7:0] out_spi_data, //the data to send to the flash
    input wire in_spi_ready, //tells fsm controller is ready to send data

    //Recv, MISO side for read key, read text commands
    input wire in_spi_valid, //tell the fsm the out_data is valid
    input wire [7:0] in_spi_data, //data to send to fsm
    output wire out_spi_ready, //fsm tells the controller it is ready to receive the data

    // only for testing error output
    output reg err_flag
);
    // initial begin
    //     $dumpfile("mem_txn_fsm.vcd");
    //     $dumpvars(0, mem_txn_fsm);
    // end
    //flash opcodes
    localparam [7:0] OPC_ENABLE_RESET = 8'h66;
    localparam [7:0] OPC_RESET = 8'h99;
    localparam [7:0] OPC_WREN = 8'h06;
    localparam [7:0] OPC_GLOBAL_UNLOCK = 8'h98; 
    localparam [7:0] OPC_QE = 8'h31; // write sr2
    localparam [7:0] FLASH_RDSR2 = 8'h35; // read sr2
    localparam [7:0] FLASH_READ = 8'h6B; //fast read quad output (needs 8 dummy)
    localparam [7:0] FLASH_PP = 8'h32; //quad input page program (no dummy)
    localparam [7:0] FLASH_RDSR = 8'h05; //read sr1
    localparam [7:0] OPC_CHIP_ERASE = 8'h60; //chip erase

    // start up sequence
    localparam start = 5'd0, rst_ena = 5'd2, rst = 5'd3,
    global_unlock = 5'd4, chip_erase = 5'd5, rd_sr2_send = 5'd6,
    rd_sr2_rd = 5'd7, wr_sr2_opcode = 5'd8, wr_sr2_data = 5'd9;
    // normal workflow
    localparam idle = 5'd10, dummy = 5'd15, receive_data = 5'd16, send_data = 5'd17, wait_done = 5'd18;

    // shared subroutines / error
    localparam wren = 5'd25,send_opcode = 5'd11, send_a1 = 5'd12, send_a2 = 5'd13, send_a3 = 5'd14, 
    gap = 5'd19, wip_poll_send = 5'd20, wip_poll_rd = 5'd21, 
    wip_poll_wait = 5'd22, spi_wait = 5'd23,err  = 5'd24;

    //waiting time constant 
    // gap
    // localparam [26:0] power_on = 27'd2000000; // 4 times of minimum
    localparam [26:0] opcode_gap = 27'd5; //opcode gap 

    // wip poll
    // localparam [26:0] page_program = 27'd40000; // page program max 3ms typ 0.4ms
    localparam [7:0] pp_max = 8'd8;
    localparam [26:0] rst_t = 27'd100; //30us max poll per 10 us
    localparam [7:0] rst_t_max = 8'd3;  
    // localparam [26:0] write_sr = 27'd1000000; // write sr typ 10ms max 15ms
    localparam [7:0] wrsr_max = 8'd2;  

    // localparam [26:0] chip_erase_t = 27'd100_000_000; // poll every 1 second chip erase typ 40s max 200s comment out for now to not kill simulation
    // localparam [26:0] chip_erase_t = 27'd20_000_000; // 200ms will be comment out later this is just for simulation
    localparam [7:0] cpe_max = 8'd150;    

    `ifdef SIMULATION
        localparam [26:0] power_on      = 27'd2000;      // 2,000 cycles  (20 µs)
        localparam [26:0] page_program  = 27'd400;       // etc.
        localparam [26:0] write_sr      = 27'd10000;
        localparam [26:0] chip_erase_t  = 27'd20000;
        initial $display("SIMULATION is ON in %m");
    `else
        localparam [26:0] power_on      = 27'd2000000;   // real values
        localparam [26:0] page_program  = 27'd40000;
        localparam [26:0] write_sr      = 27'd1000000;
        localparam [26:0] chip_erase_t  = 27'd20000000;
        // localparam [26:0] power_on      = 27'd20000;      // 2,000 cycles  (20 µs)
        // localparam [26:0] page_program  = 27'd4000;       // etc.
        // localparam [26:0] write_sr      = 27'd100000;
        // localparam [26:0] chip_erase_t  = 27'd200000;
        initial $display("SIMULATION is OFF in %m");
    `endif

    
    // wip poll type
    localparam [2:0] none = 3'd0;  // no polling operation 
    localparam [2:0] pp = 3'd1;   // page program
    localparam [2:0] reset = 3'd2; // reset
    localparam [2:0] wrsr = 3'd3; // write status reg
    localparam [2:0] cpe = 3'd4;  // chip erase   

    // module id
    localparam mem_id = 2'd0, sha_id = 2'd1, aes_id = 2'd2;
    // cu opcode
    localparam RD_KEY = 2'b00, RD_TEXT = 2'b01, WR_RES = 2'b10, INVALID = 2'b11;

    // current state
    reg [4:0] state = 5'd0 ,next_state = 5'd0;
    // state to return to from wren
    reg [4:0] wren_return_state = 5'd0, n_wren_return_state = 5'd0;
    // state to return to from spi- wait- gap
    reg [4:0] gap_return_state = 5'd0, n_gap_return_state = 5'd0;    
    // state to return to from wip
    reg [4:0] wip_return_state = 5'd0, n_wip_return_state = 5'd0;  
    // state to return to after opcode + 3 address bytes
    reg [4:0] opaddr_return_state, n_opaddr_return_state; 

    // counter
    reg [26:0] counter = 27'd0, n_counter = 27'd0;
    reg [7:0] timeout_counts = 8'd0, n_timeout_counts = 8'd0;
    reg [5:0] total_bytes_left = 6'd0, n_total_bytes_left = 6'd0; // count down to 0 

    // cmd latched
    reg [7:0] opcode_q = 8'd0, n_opcode_q = 8'd0;
    reg [23:0] addr_q = 24'd0, n_addr_q = 24'd0;
    // data reg
    reg[7:0] data = 8'd0, n_data = 8'd0;
    // next for registered output
    reg[7:0] n_out_spi_data = 8'd0,n_out_cu_data = 8'd0;
    reg n_out_spi_valid = 1'd0,n_out_cu_valid = 1'd0;
    // keep track type of poll
    reg [2:0] wip_poll_type = 3'd0, n_wip_poll_type = 3'd0;
    
    reg n_err_flag = 1'b0, n_qed = 1'b0;

    // to be changed for back pressure
    // cu to fsm only high when idle or send data when spi is ready or the buffer is empty
    assign out_cu_ready  = (state == idle) || (state == send_data && (!out_spi_valid));
    // spi to fsm only high when receiving data of single handshake state during start up or
    // receive data sates when cu is ready or buffer to cu is empty
    assign out_spi_ready = (state == rd_sr2_rd) || (state == wip_poll_rd) || (state == dummy)
    || (state == receive_data && (!out_cu_valid || in_cu_ready));
    
    wire cu_empty_next; // output to cu will be empty after this cycle in read flow
    assign cu_empty_next = !out_cu_valid || (out_cu_valid && in_cu_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data <= 8'd0;
            // state
            state <= start;
            wren_return_state <= 0;
            gap_return_state <= 0;
            wip_return_state <= 0;
            opaddr_return_state <= 0;
            // data out  
            out_cu_valid <= 0;
            out_cu_data <= 0;
            out_spi_valid <= 0;
            out_spi_data <= 0;
            // counter
            counter <= 0;
            timeout_counts <= 0;
            total_bytes_left <= 0;

            opcode_q <= 0;
            addr_q <= 0;
            wip_poll_type <= 0;
            // only for testing
            err_flag <= 0;
            // quad enabled signal
            qed <= 0;
        end else begin
            // state
            state <= next_state;
            wren_return_state <= n_wren_return_state;
            gap_return_state <= n_gap_return_state;             
            wip_return_state <= n_wip_return_state;
            opaddr_return_state <= n_opaddr_return_state;
            // data out
            out_spi_data <= n_out_spi_data;
            out_spi_valid <= n_out_spi_valid;
            out_cu_data <= n_out_cu_data;
            out_cu_valid <= n_out_cu_valid;
            // counter
            counter <= n_counter;
            timeout_counts <= n_timeout_counts;
            total_bytes_left <= n_total_bytes_left;

            wip_poll_type <= n_wip_poll_type; 
            data <= n_data;

            // opcode/data latch
            addr_q <= n_addr_q;
            opcode_q <= n_opcode_q;

            // only for testing
            err_flag <= n_err_flag;
            // quad enabled signal
            qed <= n_qed;
        end
    end
    
    always @(*) begin
        // default
        // state
        next_state = state;
        n_wren_return_state = wren_return_state;
        n_gap_return_state = gap_return_state;
        n_wip_return_state = wip_return_state;
        n_opaddr_return_state = opaddr_return_state;
        // 
        n_wip_poll_type  = wip_poll_type;
        // counter
        n_counter = counter;
        n_timeout_counts = timeout_counts;
        n_total_bytes_left = total_bytes_left;

        // handshake
        n_out_spi_valid = out_spi_valid;
        n_out_spi_data  = out_spi_data;
        n_out_cu_valid  = out_cu_valid;
        n_out_cu_data   = out_cu_data;
        in_fsm_done = (state == gap && gap_return_state == idle && counter == 0 && cu_empty_next); 
        in_start = 0;         
        r_w = 1'b0;
        quad_enable = 1'b0;
        // test
        n_err_flag = 0;  
        // data latch
        n_data = data;
        // opcode/addr
        n_addr_q =  addr_q;
        n_opcode_q = opcode_q; 
        // qed
        n_qed = qed; //latch to 1 after qe sent
        case (state)
            // err only for testing timeout it should never happen 
            err:begin
                in_start = 1'b0;
                r_w = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_valid = 1'b0;
                n_out_cu_valid = 1'b0;
                n_err_flag = 1'b1;  // latched error
                next_state = err;                
            end
            // shared subroutines

            // send read status reg 1 opcode
            wip_poll_send: begin
                in_start = 1;
                r_w = 0;
                quad_enable = 0;
                next_state = (in_spi_ready) ? wip_poll_rd : wip_poll_send;
                n_out_spi_data = FLASH_RDSR;
                n_out_spi_valid = 1;
            end 
            // read wip 
            wip_poll_rd: begin  
                in_start = 1;
                r_w = 1;
                quad_enable = 0;
                n_out_spi_valid = 0;
                if (in_spi_valid) begin
                    if (in_spi_data[0]) begin
                        case (wip_poll_type)
                            none: next_state = err; // not suppose to in this stage
                            // page program
                            pp: begin
                                n_counter = page_program;
                                next_state = (timeout_counts>=pp_max) ? err : wip_poll_wait;
                            end
                            // write status register
                            wrsr: begin
                                n_counter = write_sr;
                                next_state = (timeout_counts>=wrsr_max) ? err : wip_poll_wait;
                            end
                            // software reset
                            reset: begin
                                n_counter = rst_t;
                                next_state = (timeout_counts>=rst_t_max) ? err : wip_poll_wait;
                            end   
                            //chip erase                                         
                            cpe: begin
                                n_counter = chip_erase_t;
                                next_state = (timeout_counts>=cpe_max) ? err : wip_poll_wait;
                            end
                            default:next_state = err; // why are we here 
                        endcase
                        n_timeout_counts = timeout_counts + 1;
                    end else begin
                        // give opcode gap
                        next_state = gap;
                        n_gap_return_state = wip_return_state;
                        n_counter = opcode_gap;
                        n_timeout_counts = 0;
                    end
                end
            end     
            // wait for next poll         
            wip_poll_wait: begin    
                in_start = 0;
                r_w = 0;
                if (counter == 0) begin
                    next_state = wip_poll_send;
                end else begin
                    n_counter = counter - 1;
                    next_state = wip_poll_wait;
                end
            end  
            // wait signal being transfered/spi finish last byte
            spi_wait: begin
                in_start = 1;
                n_out_spi_valid = 0;
                if (in_spi_done) begin
                    // transaction completed, go next without deassert cs
                    next_state = gap;
                    n_counter = opcode_gap; // 50ns, minimum requirement of flash after cs goes high
                end                
            end
            // gap to make cs high
            gap:begin
                in_start = 0; // cs high
                n_counter = (counter == 0) ? 0 : counter - 1;
                next_state = (counter == 0 && cu_empty_next) ? gap_return_state : gap; 
                // clear out cu valid if the fsm finish all the byte but cu havent take it
                if (out_cu_valid && in_cu_ready)
                    n_out_cu_valid = 1'b0;
            end
            // send write enable
            wren: begin
                in_start = 1;
                r_w = 0;
                quad_enable = 0;
                n_out_spi_data = OPC_WREN;
                n_out_spi_valid =  1;
                next_state = in_spi_ready ? spi_wait : wren;
                n_gap_return_state = wren_return_state;
            end
            // send opcode+addr
            send_opcode: begin
                in_start = 1'b1;
                r_w  = 1'b0; // command/address phase = write
                quad_enable = 1'b0;

                // launch byte if not currently valid
                if (!out_spi_valid) begin
                    n_out_spi_data  = opcode_q;
                    n_out_spi_valid = 1'b1;
                end

                // handshake -> consume this byte
                if (out_spi_valid && in_spi_ready) begin
                    n_out_spi_valid = 1'b0;
                    next_state = send_a1;
                end             
            end
            // send addr 23:16
            send_a1: begin
                in_start = 1'b1;
                r_w = 1'b0;
                quad_enable = 1'b0;
                // launch byte if not currently valid
                if (!out_spi_valid) begin
                    n_out_spi_data  = addr_q[23:16];
                    n_out_spi_valid = 1'b1;
                end

                // handshake -> consume this byte
                if (out_spi_valid && in_spi_ready) begin
                    n_out_spi_valid = 1'b0;
                    next_state = send_a2;
                end 
            end
            // send addr 15:8
            send_a2: begin
                in_start  = 1'b1;
                r_w = 1'b0;
                quad_enable = 1'b0;
                // launch byte if not currently valid
                if (!out_spi_valid) begin
                    n_out_spi_data  = addr_q[15:8];
                    n_out_spi_valid = 1'b1;
                end

                // handshake -> consume this byte
                if (out_spi_valid && in_spi_ready) begin
                    n_out_spi_valid = 1'b0;
                    next_state = send_a3;
                end 
            end
            // send addr 7:0
            send_a3: begin
                in_start = 1'b1;
                r_w = 1'b0;
                quad_enable = 1'b0;
                // launch byte if not currently valid
                if (!out_spi_valid) begin
                    n_out_spi_data  = addr_q[7:0];
                    n_out_spi_valid = 1'b1;
                end

                // handshake -> consume this byte
                if (out_spi_valid && in_spi_ready) begin
                    n_out_spi_valid = 1'b0;
                    next_state = opaddr_return_state;
                end 
            end
            // start up flow
            // power on
            start: begin
                // wait power on time
                in_start    = 1'b0; // CS high during power-on wait
                r_w         = 1'b0;
                quad_enable = 1'b0;
                next_state = gap;
                n_gap_return_state = wren;
                n_wren_return_state = rst_ena; // must send wren before send reset ena
                n_counter = power_on;
            end 
            // send reset enable 
            rst_ena: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = OPC_ENABLE_RESET;
                n_out_spi_valid = 1;
                n_gap_return_state = rst; // no wren need to send after rst ena sent
                next_state = in_spi_ready? spi_wait:rst_ena;        
            end
            // send reset
            rst: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = OPC_RESET;
                n_out_spi_valid = 1;    
                // after reset, check status reg 1 until wip is 0, then send wren, and eventually ends at global unlock
                n_wren_return_state = global_unlock; 
                n_gap_return_state = wip_poll_send;
                n_wip_return_state = wren;
                next_state = in_spi_ready? spi_wait: rst;   
                n_wip_poll_type = reset;     
            end   
            // global unlock
            global_unlock: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = OPC_GLOBAL_UNLOCK;
                n_out_spi_valid = 1;      
                next_state = in_spi_ready ? spi_wait : global_unlock;
                n_gap_return_state = wren; // no need to wait for certain us scale, 50ns is enough
                n_wren_return_state = chip_erase; // 
            end
            // chip erase
            chip_erase: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = OPC_CHIP_ERASE;
                n_out_spi_valid = 1;
                next_state = in_spi_ready ? spi_wait : chip_erase;
                n_gap_return_state = wip_poll_send;
                n_wip_return_state = rd_sr2_send; // after chip erase done go straight into read status reg 2
                n_wip_poll_type = cpe;
            end
            // send read status reg 2
            rd_sr2_send: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = FLASH_RDSR2;
                n_out_spi_valid = 1;
                next_state = in_spi_ready ? rd_sr2_rd : rd_sr2_send; // after cmd send go to waiting for status reg input             
            end
            //process status reg 2 
            rd_sr2_rd: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b1; // read
                quad_enable = 1'b0;
                if (in_spi_valid) begin
                    n_data = {in_spi_data[7:2],1'b1,in_spi_data[0]}; // change qe bit of sr2 data[7:0]
                    next_state = spi_wait;
                    n_gap_return_state = wren;
                    n_wren_return_state = wr_sr2_opcode; // now go to write status reg 2
                end                
            end 
            // write to status reg 2
            wr_sr2_opcode: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = OPC_QE; 
                n_out_spi_valid = 1;
                next_state = in_spi_ready? wr_sr2_data: wr_sr2_opcode; // send modified wrsr2 after opcode sent
            end  
            // write status reg2 data
            wr_sr2_data: begin
                in_start    = 1'b1; // CS low
                r_w         = 1'b0;
                quad_enable = 1'b0;
                n_out_spi_data = data; // qe bit 1 sr2
                n_out_spi_valid = 1;   
                next_state = in_spi_ready? spi_wait: wr_sr2_data;
                n_gap_return_state = wip_poll_send; // go poll
                n_wip_poll_type = wrsr; // write status reg timing
                n_wip_return_state = idle; // after everything finished, go to normal flow idle
                n_qed = in_spi_ready? 1: 0;
            end

            // normal flow
            // idle state: decode opcode from cu into operation and size of transaction
            idle: begin
                n_out_cu_data = 0;
                n_out_cu_valid = 0;
                n_out_spi_data = 0;
                n_out_spi_valid = 0;
                if(in_cu_valid && out_cu_ready) begin
                    case (in_cu_data[1:0])
                        RD_KEY: begin
                            n_total_bytes_left = 32;
                            n_opcode_q = FLASH_READ;
                            n_addr_q = out_address;
                            next_state = wip_poll_send; // ppll wip until not busy 
                            n_wip_poll_type = pp; // page programm 
                            n_wip_return_state = send_opcode;
                            n_opaddr_return_state = dummy;
                        end 

                        RD_TEXT:begin
                            n_total_bytes_left = (in_cu_data[3:2] == aes_id) ? 16 : 32; // aes rd txt 16B sha rd txt 32B
                            n_opcode_q = FLASH_READ;
                            n_addr_q = out_address;
                            next_state = wip_poll_send; // ppll wip until not busy 
                            n_wip_poll_type = pp; // page programm 
                            n_wip_return_state = send_opcode;
                            n_opaddr_return_state = dummy;                            
                        end
                        WR_RES: begin
                            n_total_bytes_left = (in_cu_data[5:4] == aes_id) ? 16 : 32; // aes wr txt 16B sha wr txt 32B
                            n_opcode_q = FLASH_PP;
                            n_addr_q = out_address;
                            next_state = wip_poll_send; // ppll wip until not busy 
                            n_wip_poll_type = pp; // page programm 
                            n_wip_return_state = wren; // send wren before writing
                            n_wren_return_state = send_opcode;
                            n_opaddr_return_state = send_data;                                  
                        end
                        INVALID: next_state = idle;
                        default:; 
                    endcase
                end
            end
            // dummy set spi to read mode but dont give shit to data, only for quad output read
            dummy: begin
                in_start = 1'b1;
                r_w = 1'b1; //dummy dont care 1 byte for quad output read
                quad_enable = 1'b0;
                next_state = (in_spi_valid && out_spi_ready) ? receive_data : dummy;
            end
            // receive data from spi: handshake to both cu and spi
            receive_data:begin
                in_start = 1'b1;
                r_w = 1'b1; // read
                quad_enable = 1'b1;   // quad output
                
                // reset valid after handshake at cu
                if (out_cu_valid && in_cu_ready) begin
                    n_out_cu_valid = 1'b0;   // byte has been consumed
                end

                // fsm - spi handshake
                if(out_spi_ready && in_spi_valid) begin
                    n_out_cu_data = in_spi_data;
                    n_out_cu_valid = 1;

                    if (total_bytes_left == 1) begin
                        n_total_bytes_left = 0;
                        // go to opcode gap
                        next_state = gap;
                        n_counter = opcode_gap;
                        n_gap_return_state = idle;

                    end else begin
                        n_total_bytes_left = total_bytes_left - 1;
                    end

                end
            end
            // send data to flash from cu to spi
            send_data: begin
                in_start = 1'b1;
                r_w = 1'b0; // write
                quad_enable = 1'b1;   // quad output

                // fsm - spi handshake reset
                if (out_spi_valid && in_spi_ready) begin
                    n_out_spi_valid = 0;

                    // go to gap after all data being transfer to spi
                    if (total_bytes_left == 0) begin 
                        next_state = spi_wait;
                        n_gap_return_state = idle;

                    end
                end 

                // fsm - cu handshake
                if (in_cu_valid && out_cu_ready) begin
                    n_out_spi_data = in_cu_data;
                    n_out_spi_valid = 1'b1;
                    n_total_bytes_left = total_bytes_left - 1;
                end
            end

            default: ;
        endcase
    end
endmodule