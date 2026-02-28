/*
 * Copyright (c) 2024 UWASIC
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_mem_toplevel(
    input  wire [7:0] ui_in,     // Dedicated inputs
    output wire [7:0] uo_out,    // Dedicated outputs
    input  wire [7:0] uio_in,    // IOs: Input path
    output wire [7:0] uio_out,   // IOs: Output path
    output wire [7:0] uio_oe,    // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,       // always 1 when the design is powered
    input  wire       clk,       // clock
    input  wire       rst_n      // reset_n - low to reset
);

  // ----------------------------
  // Internal wires from mem_top
  // ----------------------------
  wire        valid;
  wire [7:0]  data;
  wire        ready_in;
  wire        ack_valid;
  wire [1:0]  module_source_id;

  wire        cs;
  wire        sclk;
  wire        out0, out1, out2, out3;
  wire [3:0]  flash_uio_oe;
  wire        err;

  // ----------------------------
  // Instantiate your real top
  // ----------------------------
  mem_top u_mem_top (
      .clk(clk),
      .rst_n(rst_n),

      // Bus side
      .READY(ui_in[0]),      // placeholder input
      .VALID(valid),
      .DATA(data),

      .READY_IN(ready_in),
      .VALID_IN(ui_in[1]),   // placeholder input
      .DATA_IN(ui_in),       // placeholder input bus

      // Ack side
      .ACK_READY(ui_in[2]),  // placeholder input
      .ACK_VALID(ack_valid),
      .MODULE_SOURCE_ID(module_source_id),

      // Flash side
      .CS(cs),
      .SCLK(sclk),

      .IN0(uio_in[0]),
      .IN1(uio_in[1]),
      .IN2(uio_in[2]),
      .IN3(uio_in[3]),

      .OUT0(out0),
      .OUT1(out1),
      .OUT2(out2),
      .OUT3(out3),

      .uio_oe(flash_uio_oe),

      // test only
      .err(err)
  );

  // ----------------------------
  // Map outputs to Tiny Tapeout pins
  // ----------------------------
  assign uo_out[0]   = valid;
  assign uo_out[7:1] = data[6:0];   // just placeholder packing

  assign uio_out[0] = out0;
  assign uio_out[1] = out1;
  assign uio_out[2] = out2;
  assign uio_out[3] = out3;
  assign uio_out[4] = cs;
  assign uio_out[5] = sclk;
  assign uio_out[6] = ack_valid;
  assign uio_out[7] = err;

  assign uio_oe[3:0] = flash_uio_oe;
  assign uio_oe[4]   = 1'b1;  // cs output
  assign uio_oe[5]   = 1'b1;  // sclk output
  assign uio_oe[6]   = 1'b1;  // ack_valid output
  assign uio_oe[7]   = 1'b1;  // err output

  // Prevent unused-input warnings
  wire _unused = &{ena, data[7], ready_in, module_source_id, 1'b0};

endmodule
