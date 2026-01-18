import cocotb,random
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
from cocotb.simtime import get_sim_time

async def SPI_no_addr(dut):
    # Get opcode without addr
    dut._log.info("SPI Opcode Collect")
    await FallingEdge(dut.out_cs_n)
    opcode = 0x00   
    for _ in range(8):
        await RisingEdge(dut.out_sclk)
        opcode = (opcode << 1) | int(int(dut.out_io.value) & 0b0001)
        assert int(dut.io_ena.value) == 0xf, f"uio_oe expected 0xf got {int(dut.uio_oe.value):#01x}"
    t = get_sim_time(unit='ns')
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
            await FallingEdge(dut.out_sclk)
            await RisingEdge(dut.out_sclk)
            byte = (byte << 1) | int(int(dut.out_io.value) & 0b0001)
            if(dut.qed.value == 0):
                assert int(dut.io_ena.value) == 0b1101, f"uio_oe expected 0b1101 got {int(dut.io_ena.value):#04b}"
            else:
                assert int(dut.io_ena.value) == 0b0001, f"uio_oe expected 0b1101 got {int(dut.io_ena.value):#04b}"
        data.append(byte)
    return data

async def check_qspi_idle(dut, cycles=10):
    """ 
    Expect io_ena   after out_cs_n high
    """
    for _ in range(cycles):
        await RisingEdge(dut.clk)

        # cs high
        assert dut.out_cs_n.value == 1, f"Idle: out_cs_n expected 1, got {dut.out_cs_n.value}"
        # sclk 0
        assert dut.out_sclk.value == 1, f"Idle: out_sclk expected 1, got {dut.out_sclk.value}"
        # no io pins
        oe = int(dut.io_ena.value) & 0xF
        assert oe == 0x0, f"Idle: io_ena[3:0] expected 0000, got {oe:04b}"

async def rdsr(dut,data,header):
    dut._log.info("Rd SR Opcode")
    await FallingEdge(dut.out_cs_n)
    # opcode
    opcode = 0x00   


    for _ in range(8):
        # data being updated on the fall edge, so check after the falledge 
        await FallingEdge(dut.out_sclk)
        # emulate flash sample on this edge （）
        await RisingEdge(dut.out_sclk)
 
        opcode = (opcode << 1) | int(int(dut.out_io.value) & 0b0001)
        # dut._log.info(f"out_io {int(int(dut.out_io.value) & 0b0001)}")
        assert int(dut.io_ena.value) == 0b1101, f"io_ena expected 0b1101 got {int(dut.io_ena.value):#04b}"
    t = get_sim_time(unit='ns')
    dut._log.info(f"[{t} ns] Opcode {opcode:#08b}, exp opcode = {header:#08b}")
    dut._log.info("Rd SR Shift In")

    # drive io1 on 8th falledge
    for b in range(8):
        # flash updates on the 9th fall edge , AND spi sample on the 10th rise edge
        # (int(dut.in_io.value) >> 1) & 1 == 0b1 & (data >> (7-b))
        await FallingEdge(dut.out_sclk)
        dut.in_io.value = ((0b1 & (data >> (7-b))) << 1) & 0b0010
        # dut._log.info(f"in_io {(int(dut.in_io.value) >> 1) & 1}")
        await RisingEdge(dut.out_sclk)
        
        
        assert int(dut.io_ena.value) == 0b1101, f"io_ena expected 0b1101 got {int(dut.io_ena.value):#04b}"

    t = get_sim_time(unit='ns')
    dut._log.info(f"[{t} ns] exp data shifted in {data:#08b}")
    dut._log.info("Rd SR Flow Done") 
    return opcode 

async def wrsr(dut):
    # Get opcode with addr
    dut._log.info("SPI Opcode Collect")
    await FallingEdge(dut.out_cs_n)
    opcode = 0x00   
    for _ in range(8):
        await FallingEdge(dut.out_sclk)
        await RisingEdge(dut.out_sclk)
        opcode = (opcode << 1) | int(int(dut.out_io.value) & 0b0001)
        assert int(dut.io_ena.value) == 0b1101, f"io_ena expected 0b1101 got {int(dut.io_ena.value):#04b}"
    t = get_sim_time(unit='ns')
    dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")

    data = 0
    for _ in range(8):
        await FallingEdge(dut.out_sclk)
        await RisingEdge(dut.out_sclk)
        data = (data << 1) | int(int(dut.out_io.value) & 0b0001)
        assert int(dut.io_ena.value) == 0b1101, f"io_ena expected 0b1101 got {int(dut.io_ena.value):#04b}"
    # Timestamp
    t = get_sim_time(unit='ns')
    dut._log.info(f"[{t} ns] Opcode = 0x{opcode:02X}, Data = 0x{data:02X}") 
    return opcode, data

async def get_data(dut):
    await RisingEdge(dut.out_rx_valid)
    t = get_sim_time(unit='ns')
    # dut._log.info(f" out rx valid @ [{t} ns]")
    # dut._log.info(f"[{t} ns] data from dut {int(dut.out_rx_data.value):#08b}")
    return int(dut.out_rx_data.value)

async def quad_out_sample(dut):
    dut._log.info("Quad Output Sample Start")  
    await FallingEdge(dut.out_cs_n)
    for _ in range(8+24):
        await FallingEdge(dut.out_sclk)
        await RisingEdge(dut.out_sclk)
    data=[] 
    for i in range(8):
        byte = 0
        for _ in range(2):
            # each sclk sample 4 b
            await FallingEdge(dut.out_sclk)
            
            byte = (byte << 4) | (int(dut.out_io.value) & 0xf)
            await RisingEdge(dut.out_sclk)
        t = get_sim_time(unit='ns')
        dut._log.info(f" byte {i+1} sent @ [{t} ns]")
        data.append(byte)

    dut._log.info("Quad Output Sample Complete") 
    return data

async def send_byte(dut, val, timeout_cycles=2000):
    # wait for ready with a timeout
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        if int(dut.out_tx_ready.value) == 1:
            break
    else:
        raise cocotb.result.TestFailure("Timeout waiting for out_tx_ready")

    dut.in_tx_data.value = val
    dut.in_tx_valid.value = 1
    await RisingEdge(dut.clk)
    dut.in_tx_valid.value = 0

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
    dut.qed.value = 1
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

    await RisingEdge(dut.out_done)
    dut.in_tx_valid.value = 0 
    dut.in_start.value = 0
    await RisingEdge(dut.clk)
    dut._log.info("Quad Output Complete")  

async def quad_in(dut,data):
    # qspi quad input, dut sample on falling edge
    dut._log.info("Quad Input Start")   
    await FallingEdge(dut.out_cs_n)
    for _ in range(8+24):
        await RisingEdge(dut.out_sclk)
    a = 1
    for i in data:
        for b in range(2):
            await FallingEdge(dut.out_sclk)
            dut.in_io.value = ((i >> 4*(1-b)) & 0xf)
            # each sclk shift 4 b
            oe = int(dut.io_ena.value) & 0xF
            assert oe == 0x0, f"io_ena[3:0] expected 0000, got {oe:04b}"
            await RisingEdge(dut.out_sclk)  
        # t = get_sim_time(unit='ns')
        # dut._log.info(f" byte{a} sent @ [{t} ns]")
        a+=1         
    dut._log.info("Quad Input Complete")  


@cocotb.test(timeout_time= 100,timeout_unit='us')
async def spi(dut):
    dut._log.info("SPI Start")
    cocotb.start_soon(Clock(dut.clk, 10, 'ns').start())    
    await rst(dut)
    await wr_rd_do_di(dut)
    await wr_wr_do_do(dut)
    await wr_rd_do_io_in(dut)
    await wr_wr_do_io_in(dut)
    await check_qspi_idle(dut)
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
    await RisingEdge(dut.clk)   
    # flash
    
    assert dut.out_cs_n.value == 1, f"out_cs_n expected 1 got {dut.out_cs_n.value}" 
    assert int(dut.out_io.value) & 0b0001 == 0, f"IO0/DI expected 0 got {int(dut.out_io.value) & 0b0001}" 
    assert ((int(dut.out_io.value)>>1) & 0b0001) == 0, f"IO1/DO expected Z / 0 got {((int(dut.out_io.value)>>1) & 0b0001)}"
    assert ((int(dut.out_io.value)>>2) & 0b0001) == 1, f"IO2 expected 1 got {((int(dut.out_io.value)>>2) & 0b0001)}" 
    assert ((int(dut.out_io.value)>>3) & 0b0001) == 1, f"IO3 expected 1 got {((int(dut.out_io.value)>>3) & 0b0001)}"
    assert dut.out_sclk.value == 1, f"out_sclk expected 0 got {dut.out_sclk.value}"

    assert dut.out_tx_ready.value == 1, f"out_tx_ready expected 1 got {dut.out_tx_ready.value}"
    assert dut.out_rx_valid.value == 0, f"out_rx_valid expected 0 got {dut.out_rx_valid.value}"    
    assert int(dut.out_rx_data.value) == 0x0, f"out_rx_data expected 0 got {int(dut.out_rx_data.value):#04x}"  
 
    assert dut.out_done.value == 0, f"out_done expected 0 got {dut.out_done.value}" 

    # # tt output ena  
    assert int(dut.io_ena.value) == 0b1101, f"uio_oe expected 0b1101 got {int(dut.io_ena.value):#04b}"
    dut._log.info("Reset Done")    

async def wr_rd_do_di(dut):
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
    rdsr_task = cocotb.start_soon(rdsr(dut,data,exp))
    data_from_dut = cocotb.start_soon(get_data(dut))
    dut._log.info(f"data {data:#08b}")
    while True:
        valid = random.randint(0,1)
        await RisingEdge(dut.clk)
        if valid == 1:
            dut.in_tx_valid.value = 1
            t = get_sim_time(unit='ns')
            dut._log.info(f"in_tx_valid @ [{t} ns]")
            await RisingEdge(dut.clk)
            dut.in_tx_valid.value = 0
            break
    dut.in_rx_ready.value = 1
    await RisingEdge(dut.out_done)
    t = get_sim_time(unit='ns')
    dut._log.info(f" out done @ [{t} ns]")
    dut.r_w.value = 1
    got = await rdsr_task
    data_out = await data_from_dut
    dut.in_start.value = 0
    assert exp == got, f"Expect shift out {exp:#08b} got {got:#08b}"
    assert data == data_out, f"Expect collect  {data:#08b} got {data_out:#08b}"

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut._log.info("Single Pin WR-RD Done")

async def wr_wr_do_do(dut):
    dut._log.info("Sinlge Pin WR WR Start")
    dut.in_start.value = 1
    dut.r_w.value = 0
    dut.quad_enable.value = 0
    dut.in_tx_valid.value = 0
    byte1exp = random.randint(0,255)
    dut.in_tx_data.value = byte1exp
    byte2exp = random.randint(0,255)
    wr_wr_task = cocotb.start_soon(wrsr(dut))

    await send_byte(dut, byte1exp)
    await send_byte(dut, byte2exp)

    byte1,byte2 = await wr_wr_task

    await RisingEdge(dut.clk)
    dut.in_start.value = 0
    await RisingEdge(dut.clk)

    assert byte1 == byte1exp, f"Expect shift out {byte1exp:#01x} got {byte1:#01x}"
    assert byte2 == byte2exp, f"Expect collect  {byte2exp:#01x} got {byte2:#01x}"  
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)      
    dut._log.info("Sinlge Pin WR WR Done")

async def wr_rd_do_io_in(dut):
    # 8+24 single pin output + 8 dummy + 
    dut._log.info("Single Pin Opcode Quad Input Start")
    header = [random.randint(0,255), 0x65,0x43,0x21]
    data = [random.randint(0, 255) for _ in range(8)]
    
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
        # t = get_sim_time(unit='ns')
        # dut._log.info(f" byte {i+1} from dut @ [{t} ns]")
        i+=1
    dut.in_start.value = 0     
 
    await quad_in_task
    
    for i in range(len(header)):
        assert got_header[i] == header[i], f"header {i} expect {header[i]:#02x}, got {got_header[i]:#02x}"
        # dut._log.info(f" byte{i+1} in header confirmed")

    for i in range(len(data)):
        assert got_data[i] == data[i], f"data {i} expect {data[i]:#02x}, got {got_data[i]:#02x}"
        # dut._log.info(f" byte{i+1} in data confirmed")
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)      
    await check_qspi_idle(dut)


    dut._log.info("Single Pin Opcode Quad Input Done")

async def wr_wr_do_io_in(dut):
    dut._log.info("Single Pin Opcode Quad Output Start")
    # shift opcode + write sr with 1 byte data
    # assume no back pressure
    header = [random.randint(0,255), 0x65,0x43,0x21]
    data = [random.randint(0, 255) for _ in range(8)]

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
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk) 
    await check_qspi_idle(dut)

    dut._log.info("Single Pin Opcode Quad Output Done")

