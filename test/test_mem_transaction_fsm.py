# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from common import _reset, wait_signal_high
import common as cm

# ----------------------------------------------------------------------
# Helper: Fake SPI controller
# ----------------------------------------------------------------------

async def spi_accept_tx(dut, num_bytes):
    """Fake SPI: accept 'num_bytes' TX pulses from the FSM."""
    for _ in range(num_bytes):
        dut.in_spi_tx_ready.value = 1
        await RisingEdge(dut.clk)
        dut.in_spi_tx_ready.value = 0
        await RisingEdge(dut.clk)

async def spi_send_rx(dut, data_byte):
    """Fake SPI: send RX data for a read operation."""
    dut.in_spi_rx_data.value = data_byte
    dut.in_spi_rx_valid.value = 1
    await RisingEdge(dut.clk)
    dut.in_spi_rx_valid.value = 0

async def spi_done(dut):
    """Fake SPI: pulse spi_done."""
    dut.in_spi_done.value = 1
    await RisingEdge(dut.clk)
    dut.in_spi_done.value = 0

async def status_done(dut):
    """Fake status counter completion."""
    dut.in_status_op_done.value = 1
    await RisingEdge(dut.clk)
    dut.in_status_op_done.value = 0


# ----------------------------------------------------------------------
# Harry's Tests
# ----------------------------------------------------------------------

@cocotb.test()
async def test_reset(dut): 
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await _reset(dut)

    assert dut.out_fsm_cmd_ready.value == 1, "out_fsm_cmd_ready should be 1 after reset"
    assert dut.out_fsm_data_ready.value == 1, "out_fsm_data_ready should be 1 after reset"

    assert dut.out_wr_cp_data_valid.value == 0, "out_wr_cp_data_valid should be 0 after reset"
    assert dut.out_wr_cp_enc_type.value in (0, 1), "out_wr_cp_enc_type should be 0 or 1 after reset"

    assert dut.out_spi_start.value == 0, "out_spi_start should be 0 after reset"

    assert dut.out_spi_tx_valid.value == 0, "out_spi_tx_valid should be 0 after reset"
    assert dut.out_spi_rx_ready.value == 0, "out_spi_rx_ready should be 0 after reset"


@cocotb.test()
async def test_rd_key_command(dut):
    # Not applicable for SHA, for AES expect to take in a 256 bit key    
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = cm.RD_KEY
    dut.in_cmd_addr.value = 0xAABBCC
    
    dut.in_wr_data_valid = 1
    dut.in_cmd_data.value = 0xAABBCC

    spi_started = await wait_signal_high(dut, "out_spi_start")

    #TODO: mock interact with spi_controller 
    # Ensure the length of the transaction is correct
    # Ensure the data field to command port is correct eat time
    
    #do this 16(?) times
    got_data = await wait_signal_high(dut, 'out_wr_cp_data_valid', timeout_cycles=1500)
    assert spi_started

@cocotb.test()
async def test_rd_text_command(dut):
    # Depending on the source ID, for AES *OR* 512 bytes (padded/unpadded) for SHA 
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = cm.RD_TEXT
    dut.in_cmd_addr.value = 0xAABBCC
    
    dut.in_wr_data_valid = 1
    dut.in_cmd_data.value = 0xAABBCC

    spi_started = await wait_signal_high(dut, "out_spi_start")

    assert spi_started

@cocotb.test()
async def test_wr_res_command(dut):
    # Depending on the source ID this should: write out in 128 bits for AES *OR* 256 bits for SHA
    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = cm.WR_RES
    dut.in_cmd_addr.value = 0xAABBCC
    
    dut.in_wr_data_valid = 1
    dut.in_cmd_data.value = 0xAABBCC

    spi_started = await wait_signal_high(dut, "out_spi_start")

    assert spi_started

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

# ----------------------------------------------------------------------
# Kevin's Tests
# ----------------------------------------------------------------------

@cocotb.test()
async def test_full_read_flow(dut):
    """Complete READ: CMD + ADDR + dummy + 1-byte data."""
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    # drive command
    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = cm.RD_KEY
    dut.in_cmd_addr.value = 0x112233
    await RisingEdge(dut.clk)
    dut.in_cmd_valid.value = 0

    # wait for SPI start
    await wait_signal_high(dut, "out_spi_start")

    # FSM will send: cmd → addr2 → addr1 → addr0 → dummy → read-data

    # accept tx bytes for cmd + addr + dummy
    await spi_accept_tx(dut, 1) # cmd
    await spi_accept_tx(dut, 1) # A2
    await spi_accept_tx(dut, 1) # A1
    await spi_accept_tx(dut, 1) # A0
    await spi_accept_tx(dut, 1) # dummy

    # now FSM expects RX data
    await RisingEdge(dut.clk)
    dut.in_spi_rx_valid.value = 1
    dut.in_spi_rx_data.value = 0x5A
    await RisingEdge(dut.clk)
    dut.in_spi_rx_valid.value = 0

    # operation done
    await spi_done(dut)
    await status_done(dut)

    assert dut.out_wr_cp_data.value == 0x5A

@cocotb.test()
async def test_full_write_flow(dut):
    """Complete WRITE: pre-WREN + PP + data."""
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    dut.in_cmd_valid.value = 1
    dut.in_cmd_opcode.value = cm.WR_RES
    dut.in_cmd_addr.value = 0x556677
    await RisingEdge(dut.clk)
    dut.in_cmd_valid.value = 0

    # pre-WREN start
    await wait_signal_high(dut, "out_spi_start")
    await spi_accept_tx(dut, 1) # WREN byte
    await spi_done(dut)

    # now real Page Program
    await wait_signal_high(dut, "out_spi_start")

    # cmd + 3 bytes addr = 4 TX pulses
    await spi_accept_tx(dut, 1)  # PP opcode
    await spi_accept_tx(dut, 1)
    await spi_accept_tx(dut, 1)
    await spi_accept_tx(dut, 1)

    # now FSM asks for write data
    dut.in_wr_data_valid.value = 1
    dut.in_cmd_data.value = 0xAB

    await spi_accept_tx(dut, 1) # send data

    dut.in_wr_data_valid.value = 0

    await spi_done(dut)
    await status_done(dut)

    assert True, "WRITE flow executed successfully"