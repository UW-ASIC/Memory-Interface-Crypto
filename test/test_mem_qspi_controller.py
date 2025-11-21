# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
    #------inputs---------:
    #input clk
    #input rst_n
    #input [7:0] data_in
    #input r_w 
    #input width // 00 = standard spi, 01 = dual spi, 10 = quad spi
    #input fsm_ready
    #input fsm_valid
    #input [3:0] in //input from flash
    #-----outputs------
    #output [7:0] data_out
    #output ctrl_valid
    #output ctrl_ready 
    #ouput reg [3:0] out //output to flash
    #output reg n_cs
    #output reg sck 
#im assuming the sclk freq is half the clk freq (so it sck toggles every clk cycle)
@cocotb.test()
async def test_sck(dut):
    dut._log.info("Test sck")
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut.width.value = 0b00
    dut.r_w.value = 0
    dut.fsm_valid.value = 1
    sck_value = 0
    for i in range(16):
        assert dut.n_cs.value == 0 f"n_cs expected 0 got {dut.n_cs.value}"
        assert dut.sck.value == sck_value f"sck expected {sck_value} got {dut.sck.value}"
        sck_value = not sck_value
        await ClockCycles(dut.clk, 1)
    dut._log.info("Sck test success")

async def test_standard_spi(dut):
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    #test read with standard spi
    dut._log.info("Test Read with standard spi")
    dut.r_w.value = 0
    dut.width.value = 0b00
    dut.fsm_valid.value = 1 
    for i in range(15):
        await ClockCycles(dut.clk, 1)
        assert dut.ctrl_valid == 0
    await ClockCycles(dut.clk, 1)
    assert dut.ctrl_valid == 1 #data should be valid on 16th cycle

    dut.fsm_ready.value = 1 #set fsm_ready to high to accept the data
    await ClockCycles(dut.clk, 1)
    assert dut.ctrl_ready == 1 #make sure the ctrl is ready to start a new transaction
    assert dut.ctrl_valid == 0

    #test write with standard spi
    dut._log.info("Test Write with standard spi")
    dut.r_w.value = 1
    dut.width.value = 0b00
    dut.fsm_valid.value = 1
    dut.data_in.value = 0b01010101
    correct_values = [0b0000, 0b0001, 0b0000, 0b0001, 0b0000, 0b0001, 0b0000, 0b0001]
    for i in correct_values:
        await ClockCycles(dut.clk, 2) #sck falling edge after two clock cycles
        assert dut.out.value == i f"Expected out to be {i}, got {dut.out.value}"

async def test_dual_spi(dut):
    #test read with dual spi
    dut._log.info("Test read with dual spi")
    dut.r_w.value = 0
    dut.width.value = 0b01
    dut.fsm_valid.value = 1 
    for i in range(7):
        await ClockCycles(dut.clk, 1)
        assert dut.ctrl_valid == 0
    await ClockCycles(dut.clk, 1)
    assert dut.ctrl_valid == 1 #data should be valid on 8th cycle
    #test write with dual spi
    dut._log.info("Test Write with dual spi")
    dut.r_w.value = 1
    dut.width.value = 0b01
    dut.fsm_valid.value = 1
    dut.data_in.value = 0b01010101
    correct_values = [0b0001, 0b0001, 0b0001, 0b0001]
    for i in correct_values:
        await ClockCycles(dut.clk, 2) #sck falling edge after two clock cycles
        assert dut.out.value == i f"Expected out to be {i}, got {dut.out.value}"

async def test_quad_spi(dut):
    #test read with quad spi
    dut._log.info("Test read with quad spi")
    dut.r_w.value = 0
    dut.width.value = 0b10
    dut.fsm_valid.value = 1 
    for i in range(3):
        await ClockCycles(dut.clk, 1)
        assert dut.ctrl_valid == 0
    await ClockCycles(dut.clk, 1)
    assert dut.ctrl_valid == 1 #data should be valid on 4th cycle
    #test write with quad spi
    dut._log.info("Test Write with quad spi")
    dut.r_w.value = 1
    dut.width.value = 0b10
    dut.fsm_valid.value = 1
    dut.data_in.value = 0b01010101
    correct_values = [0b0101, 0b0101]
    for i in correct_values:
        await ClockCycles(dut.clk, 2) #sck falling edge after two clock cycles
        assert dut.out.value == i f"Expected out to be {i}, got {dut.out.value}"
