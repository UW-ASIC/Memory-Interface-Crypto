# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_reset(dut): 
    pass

@cocotb.test()
async def test_rd_key_command(dut):
    # Not applicable for SHA, for AES expect to take in a 256 bit key    
    pass

@cocotb.test()
async def test_rd_text_command(dut):
    # Depending on the source ID, for AES *OR* 512 bytes (padded/unpadded) for SHA 
    pass

@cocotb.test()
async def test_wr_res_command(dut):
    # Depending on the source ID this should: write out in 128 bits for AES *OR* 256 bits for SHA
    pass

@cocotb.test()
async def test_cp_handshake(dut):
    pass

@cocotb.test()
async def test_spi_controller_handshake(dut):
    pass
