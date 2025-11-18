# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, with_timeout
from common import _reset, wait_signal_high
import common as cm


@cocotb.test()
async def test_reset(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    assert dut.out_busy.value == 0
    assert dut.out_tx_ready.value == 1
    assert dut.out_sclk.value == 0
    assert dut.out_io == 0 #defaults to input
    assert dut.out_cs_n == 0

@cocotb.test()
async def test_spi_send_quad(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    dut.in_start.value = 1
    dut.in_tx_valid = 1

    ref_data = [0xAB, 0xCD, 0xEF]
    
    for i in range(3):
        ref = ref_data[i]
        dut.in_tx_data.value = ref
        for j in range(2):
            await with_timeout(RisingEdge(dut.clk), 10, timeout_unit="us")
            assert dut.out_io.value == ref & 0x0F
            ref = ref >> 4
    
@cocotb.test()
async def test_spi_recv_quad(dut):
    pass

@cocotb.test()
async def test_io_enable(dut):
    pass

@cocotb.test()
async def test_fsm_handshake(dut):
    pass