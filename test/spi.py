import cocotb,random
import random as pyrandom
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge,
    ReadOnly,
    FallingEdge,
    Timer,
    ClockCycles,
    with_timeout,
    SimTimeoutError,
)
from cocotb.utils import get_sim_time
from cocotb.result import TestFailure


async def SPI_no_addr(dut):
    # Get opcode without addr
    dut._log.info("SPI Opcode Collect")
    await FallingEdge(dut.out_cs_n)
    opcode = 0x00   
    for _ in range(8):
        await RisingEdge(dut.out_sclk)
        opcode = (opcode << 1) | int(dut.out_io[0].value)
        assert int(dut.io_ena.value) == 0xf, f"uio_oe expected 0xf got {int(dut.uio_oe.value):#01x}"
    t = get_sim_time(units="ns")
    dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")
    return opcode

async def SPI_opcode_addr(dut):
    # Get opcode with addr
    dut._log.info("Opcode Addr Sample")
    await FallingEdge(dut.out_cs_n)
    data = [] 
    for _ in range(4):
        byte = 0
        for _ in range(8):
            await RisingEdge(dut.out_sclk)
            byte = (byte << 1) | int(dut.out_io[0].value)
            assert int(dut.io_ena.value) == 0xf, f"io_ena expected 0xf got {int(dut.io_ena.value):#01x}"
        data.append(byte)
    return data

async def check_qspi_idle(dut, cycles=10):
    """ 
    Expect io_ena 0000 after out_cs_n high
    """
    for _ in range(cycles):
        await RisingEdge(dut.clk)

        # cs high
        assert dut.out_cs_n.value == 1, f"Idle: out_cs_n expected 1, got {dut.out_cs_n.value}"
        # sclk 0
        assert dut.out_sclk.value == 0, f"Idle: out_sclk expected 0, got {dut.out_sclk.value}"
        # no io pins
        oe = int(dut.io_ena.value) & 0xF
        assert oe == 0x0, f"Idle: io_ena[3:0] expected 0000, got {oe:04b}"

async def spi_only_di_do(dut):
    await FallingEdge(dut.out_cs_n)

    while int(dut.flash.status_reg[9].value) == 0 and dut.out_cs_n.value == 0:
        await RisingEdge(dut.out_sclk)

        assert dut.out_io[2].value == 1, f"IO2 expected 1 got {dut.out_io[2].value}" 
        assert dut.out_io[3].value == 1, f"IO3 expected 1 got {dut.out_io[3].value}"
        oe = int(dut.io_ena.value) & 0xF
        # IO2/IO3 must not be driven
        # assert (oe & 0b1100) == 0, f"SPI1 mode: IO2/3 driven unexpectedly, uio_oe={oe:04b}"

async def rdsr(dut,data):
    dut._log.info("Rd SR Opcode")
    await FallingEdge(dut.out_cs_n)
    # opcode
    opcode = 0x00   
    for _ in range(8):
        opcode = (opcode << 1) | int(dut.out_io[0].value)
        await RisingEdge(dut.out_sclk)
        assert int(dut.io_ena.value) == 0xf, f"io_ena expected 0xf got {int(dut.io_ena.value):#01x}"
    t = get_sim_time(units="ns")
    dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")
    dut._log.info("Rd SR Shift In")
    for b in range(8):
        dut.in_io[1].value = 0b1 & (data >> (7-b))
        await FallingEdge(dut.out_sclk)
        assert int(dut.io_ena.value) == 0x0, f"io_ena expected 0x0 got {int(dut.io_ena.value):#01x}"
    dut._log.info("Rd SR Flow Done") 
    return opcode 

async def wrsr(dut):
    # Get opcode with addr
    dut._log.info("SPI Opcode Collect")
    await FallingEdge(dut.out_cs_n)
    opcode = 0x00   
    for _ in range(8):
        await RisingEdge(dut.out_sclk)
        opcode = (opcode << 1) | int(dut.out_io[0].value)
        assert int(dut.io_ena.value) == 0xf, f"io_ena expected 0xf got {int(dut.io_ena.value):#01x}"
    t = get_sim_time(units="ns")
    dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")

    data = 0
    for _ in range(8):
        await RisingEdge(dut.out_sclk)
        data = (data << 1) | int(dut.out_io[0].value)
        assert int(dut.io_ena.value) == 0xf, f"io_ena expected 0xf got {int(dut.io_ena.value):#01x}"
    # Timestamp
    t = get_sim_time(units="ns")
    dut._log.info(f"[{t} ns] Opcode = 0x{opcode:02X}, Data = 0x{data:02X}") 
    return opcode, data

async def get_data(dut):
    await RisingEdge(dut.out_rx_valid)
    return int(dut.out_rx_data.value)

async def quad_out_sample(dut):
    dut._log.info("Quad Output Sample Start")  
    await FallingEdge(dut.out_cs_n)
    for _ in range(8+24):
        await RisingEdge(dut.out_sclk)
    data=[] 
    for i in range(32):
        byte = 0
        for _ in range(2):
            # each sclk sample 4 b
            await RisingEdge(dut.out_sclk)
            byte = (byte << 4) | (int(dut.out_io.value) & 0xf)
        data.append(byte)
    try:
        await with_timeout(RisingEdge(dut.out_cs_n),200,'ms')
    except SimTimeoutError:
        dut._log.error("CS never goes high after all data shifted")
        raise TestFailure("CS never goes high after all data shifted")
    dut._log.info("Quad Output Sample Complete") 
    return data


async def header_addr(dut,data):
    # send header: 8'opcode + 24'addr
    dut._log.info("Header Addr Start")   
    # input wire in_start, //start the transaction
    # input wire r_w, //1 is read, 0 is write
    # input wire quad_enable, //0 use standard, 1 use quad
    # output reg out_busy, //tell the fsm we are busy
    # output reg out_done, //tell the fsm we are done

    # //Send, MOSI side for write text commands
    # input wire in_tx_valid, //the fsm data is valid
    # input wire [7:0] in_tx_data, //the data to send to the flash    
    dut.in_start.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 0
    i = 0
    while i <len(data):
        dut.in_tx_valid.value = 1
        dut.in_tx_data.value = data [i]
        await RisingEdge(dut.clk)
        if dut.out_tx_ready.value == 1:
            i += 1

    dut.in_tx_valid.value = 0 
    dut._log.info("Header Addr Complete")

async def quad_out(dut,data):
    dut._log.info("Quad Output Start")   
    # qspi quad output stage
    # input wire in_start, //start the transaction
    # input wire r_w, //1 is read, 0 is write
    # input wire quad_enable, //0 use standard, 1 use quad
    # output reg out_busy, //tell the fsm we are busy
    # output reg out_done, //tell the fsm we are done

    # //Send, MOSI side for write text commands
    # input wire in_tx_valid, //the fsm data is valid
    # input wire [7:0] in_tx_data, //the data to send to the flash    
    dut.in_start.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 1
    i = 0
    while i <len(data):
        dut.in_tx_valid.value = 1
        dut.in_tx_data.value = data [i]
        await RisingEdge(dut.clk)
        if dut.out_tx_ready.value == 1:
            i += 1

    dut.in_tx_valid.value = 0 
    dut.in_start.value = 0
    await RisingEdge(dut.clk)
    dut._log.info("Quad Output Complete")  

async def quad_in(dut,data):
    # qspi quad input, dut sample on falling edge
    dut._log.info("Quad Input Start")   
    await FallingEdge(dut.out_cs_n)
    for _ in range(8+24+8):
        await RisingEdge(dut.out_sclk)
    for i in data:
        for b in range(2):
            # each sclk sample 4 b
            dut.in_io.value = ((i >> 4*(1-b)) & 0xf)
            await FallingEdge(dut.out_sclk)
            oe = int(dut.io_ena.value) & 0xF
            assert oe == 0x0, f"Idle: io_ena[3:0] expected 0000, got {oe:04b}"           
    try:
        await with_timeout(RisingEdge(dut.out_cs_n),200,'ms')
    except SimTimeoutError:
        dut._log.error("CS never goes high after all data shifted")
        raise TestFailure("CS never goes high after all data shifted")
    

    dut._log.info("Quad Input Complete")  


@cocotb.test()
async def spi(dut):
    dut._log.info("SPI Start")
    await rst(dut)
    await wr_rd_single_pin(dut)
    await wr_wr_single_pin(dut)
    await wr_rd_single_quad(dut)
    await wr_wr_single_quad(dut)
    dut._log.info("SPI Done")

async def rst(dut):
    dut._log.info("Reset Start")

    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)  
    # flash
    assert dut.out_cs_n.value == 1, f"out_cs_n expected 1 got {dut.out_cs_n.value}" 
    assert dut.out_io[0].value == 0, f"IO0/DI expected 0 got {dut.out_io[0].value}" 
    assert dut.out_io[1].value.is_z or dut.IO1.value == 0, f"IO1/DO expected Z / 0 got {dut.out_io[2].value}"
    assert dut.out_io[2].value == 1, f"IO2 expected 1 got {dut.out_io[2].value}" 
    assert dut.out_io[3].value == 1, f"IO3 expected 1 got {dut.out_io[3].value}"
    assert dut.out_sclk.value == 0, f"out_sclk expected 0 got {dut.out_sclk.value}"

    assert dut.out_tx_ready.value == 1, f"out_tx_ready expected 1 got {dut.out_tx_ready.value}"
    assert dut.out_rx_valid.value == 0, f"out_rx_valid expected 0 got {dut.out_rx_valid.value}"    
    assert int(dut.out_rx_data.value) == 0x0, f"out_rx_data expected 0 got {int(dut.out_rx_data.value):#04x}"  

    assert dut.out_busy.value == 0, f"out_busy expected 0 got {dut.out_busy.value}" 
    assert dut.out_done.value == 0, f"out_done expected 0 got {dut.out_done.value}" 

    # tt output ena  
    assert int(dut.io_ena.value) == 0x0, f"uio_oe expected 0x0 got {int(dut.uio_oe.value):#04x}"
    dut._log.info("Reset Done")    

async def wr_rd_single_pin(dut):
    dut._log.info("Single Pin WR-RD Start")
    # input wire in_start, //start the transaction
    # input wire r_w, //1 is read, 0 is write
    # input wire quad_enable, //0 use standard, 1 use quad
    # input wire in_tx_valid, //the fsm data is valid
    # input wire [7:0] in_tx_data, //the data to send to the flash
    # input wire [3:0] in_io,

    dut.in_start.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 0
    exp = random.randint(0,255)
    dut.in_tx_data.value = exp
    data = random.randint(0,255)

    while True:
        valid = pyrandom.randint(0,1)
        await RisingEdge(dut.clk)
        if valid == 1:
            dut.in_tx_valid.value = 1
            await RisingEdge(dut.clk)
            dut.in_tx_valid.value = 0
            break

    rdsr_task = cocotb.start_soon(rdsr(dut,data))
    data_from_dut = cocotb.start_soon(get_data(dut))

    await FallingEdge(dut.out_cs_n)
    for _ in range (8):
        await RisingEdge(dut.out_sclk)

    dut.r_w.value = 1
    dut.in_rx_ready.value = 1
    got = await rdsr_task
    data_out = await data_from_dut

    assert exp == got, f"Expect shift out {exp:#01x} got {got:#01x}"
    assert data == data_out, f"Expect collect  {data:#01x} got {data_out:#01x}"
    dut.in_start.value = 0
    await RisingEdge(dut.clk)
    dut._log.info("Single Pin WR-RD Done")

async def wr_wr_single_pin(dut):
    dut._log.info("Sinlge Pin WR WR Start")
    dut.in_start.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 0
    byte1exp = random.randint(0,255)
    dut.in_tx_data.value = byte1exp
    byte2exp = random.randint(0,255)
    dut.in_tx_valid.value = 1
    wr_wr_task = cocotb.start_soon(wrsr(dut))
    while True:
        if dut.out_tx_ready.value == 1:
            await RisingEdge(dut.clk)
            break
        await RisingEdge(dut.clk)

    dut.in_tx_data.value = byte2exp
    
    while True:
        if dut.out_tx_ready.value == 1:
            await RisingEdge(dut.clk)
            break
        await RisingEdge(dut.clk)

    byte1,byte2 = await wr_wr_task
    dut.in_start.value = 0
    await RisingEdge(dut.clk)

    assert byte1 == byte1exp, f"Expect shift out {byte1exp:#01x} got {byte1:#01x}"
    assert byte2 == byte2exp, f"Expect collect  {byte2exp:#01x} got {byte2:#01x}"        
    dut._log.info("Sinlge Pin WR WR Done")

async def wr_rd_single_quad(dut):
    # 8+24 single pin output + 8 dummy + 
    dut._log.info("Single Pin Opcode Quad Input Start")
    header = [random.randint(0,255), 0x65,0x43,0x21]
    data = [random.randint(0, 255) for _ in range(32)]

    header_task = cocotb.start_soon(SPI_opcode_addr(dut))
    quad_in_task = cocotb.start_soon(quad_in(dut,data))

    await header_addr(dut,header)
    got_header = await header_task

    dut.in_start.value = 1
    dut.r_w.value = 1
    dut.quad_enable.value = 1
    dut.in_rx_ready.value = 1
    i = 0
    got_data =[]
    while i <len(data):
        got_data.append(await get_data(dut))
        i+=1
    dut.in_start.value = 0     

    await quad_in_task

    for i in range(len(header)):
        assert got_header[i] == header[i], f"header {i} expect {header[i]:#02x}, got {got_header[i]:#02x}"

    for i in range(len(data)):
        assert got_data[i] == data[i], f"data {i} expect {data[i]:#02x}, got {got_data[i]:#02x}"

    await check_qspi_idle(dut)


    dut._log.info("Single Pin Opcode Quad Input Done")

async def wr_wr_single_quad(dut):
    dut._log.info("Single Pin Opcode Quad Output Start")
    # shift opcode + write sr with 1 byte data
    # assume no back pressure
    header = [random.randint(0,255), 0x65,0x43,0x21]
    data = [random.randint(0, 255) for _ in range(32)]

    header_task = cocotb.start_soon(SPI_opcode_addr(dut))
    qo_sample_task = cocotb.start_soon(quad_out_sample(dut))
    await header_addr(dut,header)
    got_header = await header_task
    await quad_out(dut,data)
    got_data = await qo_sample_task


    for i in range(len(header)):
        assert got_header[i] == header[i], f"header {i} expect {header[i]:#02x}, got {got_header[i]:#02x}"

    for i in range(len(data)):
        assert got_data[i] == data[i], f"data {i} expect {data[i]:#02x}, got {got_data[i]:#02x}"

    await check_qspi_idle(dut)

    dut._log.info("Single Pin Opcode Quad Output Done")

