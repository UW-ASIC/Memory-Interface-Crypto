
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

RD_KEY = 0b00
RD_TEXT = 0b01
WR_RES = 0b10
HASH_OP = 0b11

async def wait_signal_high(dut, sig_name, timeout_cycles=1000):
    for _ in range(timeout_cycles):
        if int(getattr(dut, sig_name).value) == 1:
            return True
        await ClockCycles(dut.clk, 1)
    return False

async def _reset(dut, cycles=20):
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst_n.value = 1