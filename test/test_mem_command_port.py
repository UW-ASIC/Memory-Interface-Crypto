# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from common import _reset, wait_signal_high
import common as cm


@cocotb.test()
async def test_reset(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)




@cocotb.test()
async def test_status_assignment(dut):
    pass

@cocotb.test()
async def test_status_read(dut):
    pass
