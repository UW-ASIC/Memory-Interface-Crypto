`default_nettype none
module mem_top (
    input wire clk,
    input wire rst_n,

//     # To Bus
// # ==================== OUT ==================== 
// # [9]    READY       input
// # [8]    VALID       output
// # [7:0]  DATA        output

// # ==================== IN =====================
// # [9]    READY_IN    output
// # [8]    VALID_IN    input
// # [7:0]  DATA_IN     input
    input wire READY,
    output wire VALID,
    output wire [7:0] DATA,

    output wire READY_IN,
    input wire VALID_IN,
    input wire [7:0] DATA_IN,

// # ==================== OUT ====================
// # [3]    ACK_READY        input     (1 = ready)
// # [2]    ACK_VALID        output    (1 = module sending ack)
// # [1:0]  MODULE_SOURCE_ID output

// # ==================== IN =====================
// # [2]    VALID_IN         input
// # [1:0]  SOURCE_ID_IN     input    

    input wire ACK_READY,
    output wire ACK_VALID,
    output wire [1:0] MODULE_SOURCE_ID,

// #  To Flash Input 0-3, Output 0-3
// #  Only briog to INOUT 
// #  /CS
// #  DI      (IO0)
// #  DO      (IO1)
// #  /WP     (IO2)
// #  /HOLD or /RESET (IO3)
// #  SCLK
    output wire CS,
    output wire SCLK,

    input wire IN0,
    input wire IN1,
    input wire IN2,
    input wire IN3,

    output wire OUT0,
    output wire OUT1,
    output wire OUT2,
    output wire OUT3,

    output wire [3:0] uio_oe,

    // test only
    output wire err
);
    // cu port

    // DATABUS
    // input wire in_bus_valid,
    // input wire in_bus_ready,
    // input wire [7:0] in_bus_data,

    // output reg [7:0] out_bus_data,
    // output reg out_bus_ready,
    // output reg out_bus_valid,

    // ACK
    // input wire in_ack_bus_owned,
    // output reg out_ack_bus_request,
    // output reg [1:0] out_ack_bus_id,

    // --- CU --- Transaction FSM ---
    // // --- Transaction FSM ---
    // output reg out_fsm_valid,
    // output wire out_fsm_ready,
    // output reg [7:0] out_fsm_data,

    // input wire in_fsm_ready,
    // input wire in_fsm_valid,
    // input wire [7:0] in_fsm_data,
    // input wire in_fsm_done,
    wire cu_fsm_valid;
    wire cu_fsm_ready;
    wire [7:0] cu_fsm_data;

    wire fsm_cu_valid;
    wire fsm_cu_ready;
    wire [7:0] fsm_cu_data; 
    wire fsm_cu_done;   
    // output reg out_fsm_enc_type,
    // output reg [1:0] out_fsm_opcode,
    // output reg [23:0] out_address
    wire cu_fsm_enc_type;
    wire [1:0] cu_fsm_opcode;
    wire [23:0] cu_fsm_address;


    mem_command_port cu(.clk(clk),.rst_n(rst_n),.in_bus_valid(VALID_IN),.in_bus_ready(READY),.in_bus_data(DATA_IN),
    .out_bus_data(DATA), .out_bus_ready(READY_IN), .out_bus_valid(VALID), .in_ack_bus_owned(ACK_READY), 
    .out_ack_bus_request(ACK_VALID), .out_ack_bus_id(MODULE_SOURCE_ID), .out_fsm_valid(cu_fsm_valid), .out_fsm_ready(cu_fsm_ready),
    .out_fsm_data(cu_fsm_data), .in_fsm_ready(fsm_cu_ready), .in_fsm_valid(fsm_cu_valid), .in_fsm_data(fsm_cu_data),
    .in_fsm_done(fsm_cu_done), .out_fsm_enc_type(cu_fsm_enc_type), .out_fsm_opcode(cu_fsm_opcode), .out_address(cu_fsm_address)
     );
    //  fsm port
    // // CU
    // output wire out_cu_ready,
    // input wire in_cu_valid,
    // input wire [7:0] in_cu_data,

    // input wire in_cu_ready,
    // output reg out_cu_valid,
    // output reg [7:0] out_cu_data,

    // output reg in_fsm_done,
    
    // input wire out_fsm_enc_type,
    // input wire [1:0] out_fsm_opcode,
    // input wire [23:0] out_address,

    // // QSPI

    // //---- Transaction FSM connections ----
    // output reg in_start, //start the transaction
    // output reg r_w, //1 is read, 0 is write
    // output reg quad_enable, //0 use standard, 1 use quad
    // input wire in_spi_done, //tell the fsm we are done
    // output reg qed, // tell spi its in standard spi mode drive uio oe [3:2] 11 and latch io [3:2] high
    wire fsm_spi_in_start;
    wire fsm_spi_r_w;
    wire fsm_spi_quad_enable;
    wire spi_fsm_done;
    wire fsm_spi_qed;
    // //Recv, MISO side for read key, read text commands
    // input wire in_spi_valid, //tell the fsm the out_data is valid
    // input wire [7:0] in_spi_data, //data to send to fsm
    // output wire out_spi_ready, //fsm tells the controller it is ready to receive the data
    // spi to fsm
    wire spi_fsm_valid;
    wire fsm_spi_ready;
    wire [7:0] spi_fsm_data;
    // //Send, MOSI side for write text commands
    // output reg out_spi_valid, //the fsm data is valid
    // output reg [7:0] out_spi_data, //the data to send to the flash
    // input wire in_spi_ready, //tells fsm controller is ready to send data    
    // fsm to spi 
    wire fsm_spi_valid;
    wire spi_fsm_ready;
    wire [7:0] fsm_spi_data;   


    // // only for testing error output
    // output reg err_flag

    mem_txn_fsm fsm(.clk(clk),.rst_n(rst_n),.out_cu_ready(fsm_cu_ready),.in_cu_valid(cu_fsm_valid),
    .in_cu_data(cu_fsm_data),.in_cu_ready(cu_fsm_ready),.out_cu_valid(fsm_cu_valid),.out_cu_data(fsm_cu_data),
    .in_fsm_done(fsm_cu_done),.out_fsm_enc_type(cu_fsm_enc_type),.out_fsm_opcode(cu_fsm_opcode),.out_address(cu_fsm_address),
    .in_start(fsm_spi_in_start),.r_w(fsm_spi_r_w),.quad_enable(fsm_spi_quad_enable),.in_spi_done(spi_fsm_done),
    .qed(fsm_spi_qed),.out_spi_valid(fsm_spi_valid),.out_spi_data(fsm_spi_data),.in_spi_ready(spi_fsm_ready),
    .in_spi_valid(spi_fsm_valid),.in_spi_data(spi_fsm_data),.out_spi_ready(fsm_spi_ready),.err_flag(err)    
    );
    // spi port
    // //---- Transaction FSM connections ----
    // input wire in_start, //start the transaction
    // input wire r_w, //1 is read, 0 is write
    // input wire quad_enable, //0 use di/do only, 1 use 4 pins for input/output, even in qspi mode sending opcdode and addr is still 1 pins
    // output reg out_done, //tell the fsm we are done
    // input wire qed, // 1 means qspi mode, 0 means standard spi

    // //Send, MOSI side for write text commands
    // input wire in_tx_valid, //the fsm data is valid
    // input wire [7:0] in_tx_data, //the data to send to the flash
    // output reg out_tx_ready, //tells fsm controller is ready to send data

    // //Recv, MISO side for read key, read text commands
    // output reg out_rx_valid, //tell the fsm the out_data is valid
    // output reg [7:0] out_rx_data, //data to send to fsm
    // input wire in_rx_ready, //fsm tells the controller it is ready to receive the data

    // //---- SPI flash connections ----
    // output reg out_sclk,
    // output reg [3:0] out_io,
    // input wire [3:0] in_io,
    // output reg out_cs_n,
    // output reg [3:0] io_ena
    // output reg [3:0] out_io,
    wire [3:0] spi_in_io  = {IN3, IN2, IN1, IN0}; //input io pins 
    wire [3:0] spi_out_io; // output io pins
    assign {OUT3, OUT2, OUT1, OUT0} = spi_out_io;
    mem_spi_controller spi(.clk(clk),.rst_n(rst_n),.in_start(fsm_spi_in_start),.r_w(fsm_spi_r_w),
    .quad_enable(fsm_spi_quad_enable),.out_done(spi_fsm_done),.qed(fsm_spi_qed),.in_tx_valid(fsm_spi_valid),
    .in_tx_data(fsm_spi_data),.out_tx_ready(spi_fsm_ready),.out_rx_valid(spi_fsm_valid),.out_rx_data(spi_fsm_data),
    .in_rx_ready(fsm_spi_ready),.out_sclk(SCLK),.out_cs_n(CS),.io_ena(uio_oe),.out_io(spi_out_io),.in_io(spi_in_io)
    );

endmodule