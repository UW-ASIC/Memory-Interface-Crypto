/*
 * Copyright (c) 2024 UWASIC
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_mem_toplevel(
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,   // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // All output pins must be assigned. If not used, assign to 0.
  assign uo_out  = ui_in + uio_in;  // Example: ou_out is the sum of ui_in and uio_in
  assign uio_out = 0;
  assign uio_oe  = 0;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, clk, rst_n, 1'b0};


  wire spi_start = 0;
  wire spi_done = 0;
  wire [7:0] spi_tx_data = 0;
  wire [7:0] spi_rx_data = 0;
  wire spi_tx_valid;
  wire spi_tx_ready;
  wire spi_rx_valid;
  wire spi_rx_ready;
  wire spi_rw;
  wire status_qe;
  

  mem_transaction_fsm fsm_inst(
    .clk(clk),
    .rst_n(rst_n),
    .in_spi_done(spi_done),

    .in_spi_rx_data(spi_rx_data),
    .in_spi_rx_valid(spi_rx_valid),

    .in_spi_tx_ready(spi_tx_ready);

    .out_spi_tx_data(spi_tx_data),
    .out_spi_tx_valid(spi_tx_valid),

    .out_spi_rx_ready(spi_rx_ready),
    
    .out_spi_r_w(spi_rw),
    .out_spi_start(spi_start),
    
    .out_status_qe(status_qe)
  );

  mem_spi_controller controller_inst(
    .clk(clk),
    .rst_n(rst_n)

    .in_start(out_spi_start),
    .r_w(spi_rw),
    .quad_enable(status_qe),

    .in_tx_valid(spi_tx_valid),
    .in_tx_data(spi_tx_data),
    .out_tx_ready(spi_tx_ready),
    
    .in_rx_ready(spi_rx_ready),
    .out_rx_data(spi_rx_data),
    .out_rx_valid(spi_rx_valid),

    .io_ena(uio_oe[3:0]),
    .in_io(uio_in[3:0]),
    .out_io(uio_out[3:0])
  )


endmodule
