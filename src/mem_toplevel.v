/*
 * Copyright (c) 2024 UWASIC
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module mem_toplevel(
    input wire in_bus_ready,
    input wire in_bus_valid,
    input wire [7:0] in_bus_data,

    input wire out_bus_ready,
    input wire out_bus_valid,
    input wire [7:0] out_bus_data,

    output wire [3:0] mem_qspi_output_enable,
    output wire [3:0] mem_qspi_out,
    output wire sclk_mem,
    output wire n_cs_mem,

    input wire [3:0] mem_qspi_in,

    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

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
  
  wire [9:0] data_bus;
  wire [2:0] ack_bus;
  wire ack_bus_ans;

  wire [23:0] cp_fsm_address;

  wire [7:0] cp_to_fsm_data;
  wire [7:0] fsm_to_cp_data;

  mem_command_port cmdport_inst(
    .clk(clk),
    .rst_n(rst_n),

    .in_bus_valid(in_bus_valid),
    .in_bus_ready(in_bus_ready),
    .in_bus_data(in_bus_data),

    .out_bus_valid(out_bus_valid),
    .out_bus_ready(out_bus_ready),
    .out_bus_data(out_bus_data),

    .out_ack_bus_request(ack_bus[2]),
    .out_ack_bus_id(ack_bus[1:0]),    
    .in_ack_bus_owned(ack_bus_ans),

    .out_fsm_data(cp_to_fsm_data),
    .in_fsm_data(fsm_to_cp_data),

    .out_address(cp_fsm_address)
  );

  mem_transaction_fsm fsm_inst(
    .clk(clk),
    .rst_n(rst_n),
    .in_spi_done(spi_done),

    .in_spi_rx_data(spi_rx_data),
    .in_spi_rx_valid(spi_rx_valid),

    .in_spi_tx_ready(spi_tx_ready),

    .out_spi_tx_data(spi_tx_data),
    .out_spi_tx_valid(spi_tx_valid),

    .out_spi_rx_ready(spi_rx_ready),
    
    .out_spi_r_w(spi_rw),
    .out_spi_start(spi_start),
    
    .out_status_qe(status_qe)
  );

  mem_spi_controller controller_inst(
    .clk(clk),
    .rst_n(rst_n),

    .in_start(spi_start),
    .r_w(spi_rw),
    .quad_enable(status_qe),

    .in_tx_valid(spi_tx_valid),
    .in_tx_data(spi_tx_data),
    .out_tx_ready(spi_tx_ready),
    
    .in_rx_ready(spi_rx_ready),
    .out_rx_data(spi_rx_data),
    .out_rx_valid(spi_rx_valid),

    .io_ena(mem_qspi_output_enable),
    .in_io(mem_qspi_in),

    .out_io(mem_qspi_out),
    .out_sclk(sclk_mem),
    .out_cs_n(n_cs_mem)
  );

endmodule
