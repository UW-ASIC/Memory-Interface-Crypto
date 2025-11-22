/*
 * Copyright (c) 2024 UWASIC
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_memory_interface (
    input  wire [7:0] ui_in,     // Dedicated inputs
    output wire [7:0] uo_out,    // Dedicated outputs
    input  wire [7:0] uio_in,    // IOs: Input path
    output wire [7:0] uio_out,   // IOs: Output path
    output wire [7:0] uio_oe,    // IOs: Enable path (1=output, 0=input)
    input  wire       ena,       // always 1 when powered
    input  wire       clk,       // clock
    input  wire       rst_n      // reset_n - low to reset
);

    // --------------------------
    // Bus inputs
    // --------------------------
    wire bus_valid   = ui_in[0];
    wire bus_ready   = ui_in[1];
    wire drive_bus   = ui_in[2];
    wire [7:0] in_bus_data = 8'b10101010;

    // Bus outputs
    wire [7:0] out_bus_data;
    wire out_bus_ready;
    wire out_bus_valid;

    // --------------------------
    // Ack Bus
    // --------------------------
    wire ack_bus_owned = ui_in[3];

    wire ack_bus_request;
    wire [1:0] ack_bus_id;

    // --------------------------
    // Status (unused)
    // --------------------------
    wire [6:0] status = 7'b0000000;

    // --------------------------
    // Transaction FSM inputs
    // --------------------------
    wire txn_done = ui_in[4];
    wire fsm_ready = ui_in[5];
    wire fsm_valid = ui_in[6];
    wire [7:0] in_fsm_bus_data = 8'b11110000;

    // FSM outputs
    wire drive_fsm_bus;
    wire out_fsm_ready;
    wire [7:0] out_fsm_bus_data;
    wire out_fsm_valid;

    // --------------------------
    // cmd_port outputs
    // --------------------------
    wire r_w;
    wire cmd_ena;       // renamed to avoid conflict with top-level 'ena'
    wire ena_fsm;
    wire ena_qspi;
    wire ena_status;

    // --------------------------
    // Length + Address
    // --------------------------
    wire length_valid;
    wire [8:0] length;

    wire address_valid;
    wire [23:0] address;

    // --------------------------
    // Top-level outputs
    // --------------------------
    assign uo_out  = ui_in + uio_in;
    assign uio_out = 8'b0;
    assign uio_oe  = {8{drive_bus}};   // drive when bus is owned

    // --------------------------
    // Module instantiation
    // --------------------------
    host_cmd_port cmd_port_inst(
        .clk(clk),
        .rst_n(rst_n),

        // --- Bus ---
        .bus_valid(bus_valid),
        .bus_ready(bus_ready),
        .drive_bus(drive_bus),
        .in_bus_data(in_bus_data),
        .out_bus_data(out_bus_data),
        .out_bus_ready(out_bus_ready),
        .out_bus_valid(out_bus_valid),

        // --- Ack Bus ---
        .ack_bus_owned(ack_bus_owned),
        .ack_bus_request(ack_bus_request),
        .ack_bus_id(ack_bus_id),

        // --- Status ---
        .status(status),

        // --- Transaction FSM ---
        .txn_done(txn_done),
        .fsm_ready(fsm_ready),
        .fsm_valid(fsm_valid),
        .drive_fsm_bus(drive_fsm_bus),
        .in_fsm_bus_data(in_fsm_bus_data),
        .out_fsm_ready(out_fsm_ready),
        .out_fsm_bus_data(out_fsm_bus_data),
        .out_fsm_valid(out_fsm_valid),

        // --- CMD outputs ---
        .r_w(r_w),
        .ena(cmd_ena),      // renamed to avoid conflict
        .ena_fsm(ena_fsm),
        .ena_qspi(ena_qspi),
        .ena_status(ena_status),

        // --- Length ---
        .length_valid(length_valid),
        .length(length),

        // --- Address ---
        .address_valid(address_valid),
        .address(address)
    );

    // --------------------------
    // Silence unused warnings
    // --------------------------
    wire _unused = &{
        1'b0
        // out_bus_data,
        // out_bus_ready,
        // out_bus_valid,
        // ack_bus_request,
        // ack_bus_id,
        // drive_fsm_bus,
        // out_fsm_ready,
        // out_fsm_data,
        // out_fsm_valid,
        // r_w,
        // cmd_ena,
        // ena_fsm,
        // ena_qspi,
        // ena_status,
        // length_valid,
        // length,
        // address_valid,
        // address
    };

endmodule
