# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, with_timeout
from common import _reset, wait_signal_high
import common as cm

#all tests written assuming divider = 1
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
    assert dut.out_cs_n == 1

@cocotb.test()
async def test_spi_send_quad(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    ref_data = [0xAB, 0xCD, 0xEF]
    correct_values = [0xA, 0xB, 0xC, 0xD, 0xE, 0xF]
    index = 0
    for i in range(len(ref_data)):
        ref = ref_data[i]
        dut.in_tx_data.value = ref
        dut.in_start.value = 1
        dut.in_tx_valid.value = 1
        dut.r_w.value = 0
        dut.quad_enable.value = 1
        for j in range(2):
            await ClockCycles(dut.clk, 2)
            await FallingEdge(dut.clk)
            assert dut.out_io.value == correct_values[index], f"expected out_io.value to be {correct_values[index]}, got {dut.out_io.value}"
            await RisingEdge(dut.clk)
            ref = ref >> 4
            index = index + 1
        assert dut.out_done.value == 1, f"expected out_done to be 1, got {dut.out_done.value}"
    
@cocotb.test()
async def test_spi_recv_quad(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)
    data_to_read = 0xAB
    dut.r_w.value = 1
    dut.quad_enable.value = 1
    dut.in_io = 0xB
    dut.in_start.value = 1
    await ClockCycles(dut.clk, 3)
    dut.in_io = 0xA
    await ClockCycles(dut.clk, 3)
    await ClockCycles(dut.clk, 1)
    dut.in_rx_ready.value = 1
    assert dut.out_done.value == 1
    assert dut.out_tx_ready == 0
    dut.in_start.value == 0
    assert dut.out_rx_valid.value == 1, f"expected out_rx_valid to be 1, got {dut.out_rx_valid}"
    assert dut.out_rx_data.value == 0xAB, f"expected out_rx_data to be {0xAB}, got {dut.out_rx_data}"
    await ClockCycles(dut.clk, 2)
    assert dut.out_tx_ready.value == 1


@cocotb.test()
async def test_spi_standard(dut):
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)
    data_to_send = 0b10101010
    correct_values = [1, 0, 1, 0, 1, 0, 1, 0]
    dut.in_tx_data.value = data_to_send
    dut.in_start.value = 1
    dut.in_tx_valid.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 0
    for i in range(len(correct_values)):
        await ClockCycles(dut.clk, 2)
        await FallingEdge(dut.clk)
        assert dut.out_io.value == correct_values[i], f"expected out_io.value to be {correct_values[i]}, got {dut.out_io.value}"
    await ClockCycles(dut.clk, 2)
    assert dut.out_done.value == 1, f"expected out_done to be 1, got {dut.out_done.value}"

