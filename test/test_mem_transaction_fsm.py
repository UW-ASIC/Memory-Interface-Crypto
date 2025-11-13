# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_reset(dut): 
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)

    assert dut.out_fsm_cmd_ready.value == 1
    assert dut.out_fsm_data_ready.value == 1

    assert dut.out_wr_cp_data_valid.value == 0
    assert dut.in_cp_enc_type.value == 1

    assert dut.out_spi_start.value == 0
    assert dut.out_spi_num_bytes.value == 0

    assert dut.out_spi_tx_valid.value == 0
    assert dut.out_spi_rx_ready.value == 0

    pass

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
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    pass

@cocotb.test()
async def test_spi_controller_handshake(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    pass
