`default_nettype none
module mem_vendor_test (
    input wire clk,
    input wire rst_n,

    input wire READY,
    output wire VALID,
    output wire [7:0] DATA,

    output wire READY_IN,
    input wire VALID_IN,
    input wire [7:0] DATA_IN,

    input wire ACK_READY,
    output wire ACK_VALID,
    output wire [1:0] MODULE_SOURCE_ID,


    output wire CS,
    output wire SCLK,

    inout wire IO0,
    inout wire IO1,
    inout wire IO2,
    inout wire IO3,
    output wire [3:0] uio_oe,

    // test only
    output wire err
);
    // waveform dump
    initial begin
        $dumpfile("mem_vendor_test.vcd");
        $dumpvars(1, mem_vendor_test.clk);
        $dumpvars(1, mem_vendor_test.SCLK);
        $dumpvars(1, mem_vendor_test.CS);
        
        $dumpvars(1, mem_vendor_test.DATA_IN);
        $dumpvars(1, mem_vendor_test.VALID_IN);
        $dumpvars(1, mem_vendor_test.READY_IN);

        $dumpvars(1, mem_vendor_test.READY);
        $dumpvars(1, mem_vendor_test.VALID);
        $dumpvars(1, mem_vendor_test.DATA);

        $dumpvars(1, mem_vendor_test.dut_io_oe);
        $dumpvars(1, mem_vendor_test.dut_io_out);
        $dumpvars(1, mem_vendor_test.dut_io_in);

        $dumpvars(1, mem_vendor_test.ACK_READY);
        $dumpvars(1, mem_vendor_test.ACK_VALID);

        $dumpvars(1, mem_vendor_test.top.cu_fsm_address);

        $dumpvars(1, mem_vendor_test.top.cu_fsm_valid);
        $dumpvars(1, mem_vendor_test.top.cu_fsm_data);
        $dumpvars(1, mem_vendor_test.top.fsm_cu_ready);

        $dumpvars(1, mem_vendor_test.top.fsm_cu_valid);
        $dumpvars(1, mem_vendor_test.top.fsm_cu_data);
        $dumpvars(1, mem_vendor_test.top.cu_fsm_ready);

        $dumpvars(1, mem_vendor_test.top.spi.internal_quad);
        $dumpvars(1, mem_vendor_test.top.spi.internal_rw);

        $dumpvars(0, mem_vendor_test.top.cu);

        $dumpvars(0, mem_vendor_test.top.fsm);

        $dumpvars(1, mem_vendor_test.top.fsm_cu_done);

        $dumpvars(1, mem_vendor_test.top.fsm_spi_data);
        $dumpvars(1, mem_vendor_test.top.fsm_spi_valid);
        $dumpvars(1, mem_vendor_test.top.fsm_spi_ready);

        $dumpvars(1, mem_vendor_test.top.spi_fsm_data);
        $dumpvars(1, mem_vendor_test.top.spi_fsm_valid);
        $dumpvars(1, mem_vendor_test.top.spi_fsm_ready);

        $dumpvars(1, mem_vendor_test.top.spi_fsm_done);
        $dumpvars(1, mem_vendor_test.top.fsm_spi_in_start);

        $dumpvars(1, mem_vendor_test.flash.status_reg);
        $dumpvars(1, mem_vendor_test.flash.in_byte);
        $dumpvars(1, mem_vendor_test.flash.out_byte);
        // $dumpvars(1, mem_vendor_test.top.);
        // $dumpvars(1, mem_vendor_test.top.);
    end

    wire [3:0] dut_io_out;
    wire [3:0] dut_io_oe;   // assume 1=drive, 0=Z (invert below if opposite)
    wire [3:0] dut_io_in;

    assign uio_oe = dut_io_oe;

    // Build the bidirectional “physical wires” seen by the flash model
    // Bit order: [0]=IO0, [1]=IO1, [2]=IO2, [3]=IO3
    assign IO0 = dut_io_oe[0] ? dut_io_out[0] : 1'bz;
    assign IO1 = dut_io_oe[1] ? dut_io_out[1] : 1'bz;
    assign IO2 = dut_io_oe[2] ? dut_io_out[2] : 1'bz;
    assign IO3 = dut_io_oe[3] ? dut_io_out[3] : 1'bz;

    assign dut_io_in[0] = IO0;
    assign dut_io_in[1] = IO1;
    assign dut_io_in[2] = IO2;
    assign dut_io_in[3] = IO3;
    
    pullup(IO2);
    pullup(IO3);

    W25Q128JVxIM flash (
    .CSn   (CS),    // active-low chip select
    .CLK   (SCLK),  // serial clock
    .DIO   (IO0),   // IO0 / DI
    .DO    (IO1),   // IO1 / DO
    .WPn   (IO2),   // IO2 / WP# (active low)
    .HOLDn (IO3)    // IO3 / HOLD# (active low)
    );

    mem_top top (
        .clk   (clk),
        .rst_n (rst_n),

        // Bus OUT (from bus into DUT)
        .READY (READY),

        // Bus IN (from DUT back to bus)
        .VALID (VALID),
        .DATA  (DATA),

        // Bus IN (from bus into DUT)
        .VALID_IN (VALID_IN),
        .DATA_IN  (DATA_IN),

        // Bus OUT (from DUT back to bus)
        .READY_IN (READY_IN),

        // Ack channel
        .ACK_READY        (ACK_READY),
        .ACK_VALID        (ACK_VALID),
        .MODULE_SOURCE_ID (MODULE_SOURCE_ID),

        // Flash pins (DUT drives these)
        .CS   (CS),
        .SCLK (SCLK),

        // Flash data pins: DUT samples these
        .IN0 (dut_io_in[0]),
        .IN1 (dut_io_in[1]),
        .IN2 (dut_io_in[2]),
        .IN3 (dut_io_in[3]),

        // Flash data pins: DUT drives these
        .OUT0 (dut_io_out[0]),
        .OUT1 (dut_io_out[1]),
        .OUT2 (dut_io_out[2]),
        .OUT3 (dut_io_out[3]),

        // Output enable (DUT controls tri-state)
        .uio_oe (dut_io_oe),

        // test-only
        .err (err)
    );



endmodule