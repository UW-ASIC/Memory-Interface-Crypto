# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

async def _reset(dut, cycles=10):
    dut.rst.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 1
    await ClockCycles(dut.clk, cycles)

@cocotb.test()
async def test_reset(dut): 
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    assert dut.out_fsm_cmd_ready.value == 1, "out_fsm_cmd_ready should be 1 after reset"
    assert dut.out_fsm_data_ready.value == 1, "out_fsm_data_ready should be 1 after reset"

    assert dut.out_wr_cp_data_valid.value == 0, "out_wr_cp_data_valid should be 0 after reset"
    assert dut.in_cp_enc_type.value in (0, 1), "out_wr_cp_enc_type should be 0 or 1 after reset"

    assert dut.out_spi_start.value == 0, "out_spi_start should be 0 after reset"

    assert dut.out_spi_tx_valid.value == 0, "out_spi_tx_valid should be 0 after reset"
    assert dut.out_spi_rx_ready.value == 0, "out_spi_rx_ready should be 0 after reset"


@cocotb.test()
async def test_rd_key_command(dut):
    # Not applicable for SHA, for AES expect to take in a 256 bit key    
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    pass

@cocotb.test()
async def test_rd_text_command(dut):
    # Depending on the source ID, for AES *OR* 512 bytes (padded/unpadded) for SHA 
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    pass

@cocotb.test()
async def test_wr_res_command(dut):
    # Depending on the source ID this should: write out in 128 bits for AES *OR* 256 bits for SHA
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    pass

@cocotb.test()
async def test_cp_handshake(dut):
    """Tests ready assertions when getting data from command port"""
    # Set the clock period to 10 us (100 KHz)
    await _reset(dut)

    # Ensure ready is high before driving a command
    await ClockCycles(dut.clk, 1)
    assert int(dut.out_fsm_cmd_ready.value) == 1

    # Drive a single-cycle command request
    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = 0b10 #RD_KEY
    dut.in_cmd_addr.value = 0xAABBCC
    await ClockCycles(dut.clk, 2)
    dut.in_cmd_valid.value = 0

    assert int(dut.out_fsm_cmd_ready.value) == 0

@cocotb.test()
async def test_spi_controller_handshake(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    pass
