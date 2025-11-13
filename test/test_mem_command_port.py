# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from common import _reset, wait_signal_high
import common as cm


@cocotb.test()
async def test_reset(dut):     
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    assert dut.out_bus.value == 0

    assert dut.out_cmd_fsm_valid.value == 0
    assert dut.out_cmd_fsm_opcode.value == 0
    assert dut.out_cmd_fsm_addr.value == 0
    assert dut.out_rd_fsm_ack.value == 0
    assert dut.out_wr_fsm_data.value == 0
    assert dut.out_fms_enc_type.value in (1, 0)

@cocotb.test()
async def test_rd_key_decode(dut):
    # Not applicable for SHA, for AES expect to take in a 256 bit key
    pass 

async def test_rd_text_decode(dut):
    # Depending on the source ID, for AES *OR* 512 bytes (padded/unpadded) for SHA 
    pass

@cocotb.test()
async def test_wr_res_decode(dut):
    # based on the source ID this should: write out in 128 bits for AES *OR* 256 bits for SHA
    pass

@cocotb.test()
async def test_invalid_header(dut):
    pass

@cocotb.test()
async def test_write_to_bus(dut):
    pass 

@cocotb.test()
async def test_fsm_handshake(dut):
    pass 
