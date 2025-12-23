# test plan 
# STARTUP_1
#     - Reset -> full startup sequence
#     - Check opcode order, QE set, end in IDLE, err_flag=0
# WR_AES_1
#     - WR_RES (AES, 16B), no backpressure
#     - Check: WIP poll, WREN before PP, 16 bytes to SPI, back to IDLE
# WR_SHA_1
#     - WR_RES (SHA, 32B), no backpressure
#     - Same as above, 32 bytes
# RD_KEY_1
#     - RD_KEY, 32B, no backpressure
#     - Check: WIP poll, READ+addr, 8 dummy, 32 bytes to CU, back to IDLE
# RD_TEXT_AES1
#     - RD_TEXT (AES, 16B), no backpressure
# RD_TEXT_SHA1
#     - RD_TEXT (SHA, 32B), no backpressure
# INV_OP_1
#     - INVALID opcode at IDLE
#     - Stay in IDLE, no SPI ops, err_flag=0
# RD_BP_CU_1
#     - Read (e.g., RD_KEY)
#     - CU backpressure: toggle in_cu_ready
#     - All bytes delivered in order, no extra, back to IDLE
# RD_BP_SPI_1
#     - Read
#     - SPI backpressure: gaps in in_spi_valid
#     - All bytes delivered, back to IDLE
# WR_BP_CU_1
#     - Write (WR_RES)
#     - CU slow to supply data
#     - All bytes reach SPI in order
# WR_BP_SPI_1
#     - Write
#     - SPI backpressure via in_spi_ready=0 bursts
# DONE_RD_1 (included in read flow)
#     - Read transaction
#     - in_fsm_done pulses exactly once at end (gap->IDLE)
# DONE_WR_1 (included in write flow)
#     - Write transaction
#     - Same check for write

import cocotb,random
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge,
    FallingEdge,
    Timer,
    ClockCycles,
    with_timeout,
)

RD_KEY_AES_BYTES = 32
RD_TEXT_AES_BYTES = 16
RD_TEXT_SHA_BYTES = 32
FLASH_PP = 0x32
FLASH_READ = 0x6b
WR_AES_BYTES = 16
WR_SHA_BYTES = 32

def rd_key_aes_256b():
    enc   = random.randint(0,1)
    src   = 0b10        # AES
    dest  = 0b00        # MEM
    opcode = 0b00       # RD_KEY
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def rd_text_aes_128b():
    enc   = random.randint(0,1)
    src   = 0b10
    dest  = 0b00
    opcode = 0b01       # RD_TEXT
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def rd_text_sha_256b():
    enc   = 0            # SHA ignores enc/dec
    src   = 0b01         # SHA
    dest  = 0b00         # MEM
    opcode = 0b01        # RD_TEXT
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def wr_aes_generate_128b():
    enc = random.randint(0,1)
    src = 0b00                          
    dest = 0b10
    opcode = 0b10                       # WR_RES
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def wr_sha_generate_256b():
    enc = random.randint(0,1)
    src = 0b00                         
    dest = 0b01
    opcode = 0b10                       # WR_RES
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def invalid():
    enc = random.randint(0,1)
    reserved = 0
    opcode = 11
    dest  = random.choice([0b01, 0b10, 0b11])
    src   = random.choice([0b00, 0b11])
    return (enc<<7)|(reserved<<6)|(dest<<4)|(src<<2)|opcode

def randomized_data():
    data = random.randint(0,255)
    return data


async def spi_random_cycle(dut):
    cycles = random.randint(16,20)
    for _ in range(cycles):
        await RisingEdge(dut.clk)

async def spi_wr(dut, exp: int):
    # assert output for single instruction
    # Wait valid 
    await RisingEdge(dut.out_spi_valid)
    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 0
    got = int(dut.out_spi_data.value)
    assert got == exp, f"out_spi_data expected 0x{exp:#02x}, got {got:#04x}"
    # emulate before shifting 
    await spi_random_cycle(dut)
    dut.in_spi_ready.value = 1
    await RisingEdge(dut.clk)
    # accept byte
    dut.in_spi_ready.value = 0
    # emulate sending this byte
    await spi_random_cycle(dut)
    # transaction done
    dut.in_spi_done.value = 1
    await RisingEdge(dut.clk)
    dut.in_spi_done.value = 0

async def rd_sr(dut,exp:int,data):
    # emualate read status reg, take one instruction and return one 
    await RisingEdge(dut.out_spi_valid)
    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 0
    got = int(dut.out_spi_data.value)
    assert got == exp, f"out_spi_data expected 0x{exp:02x}, got {got:#04x}"
    # emulate before shifting
    await spi_random_cycle(dut)
    # accept byte
    dut.in_spi_ready.value = 1
    await RisingEdge(dut.clk)
    dut.in_spi_ready.value = 0
    # emulate shifting current byte
    await spi_random_cycle(dut)
    # reg data
    dut.in_spi_valid.value = 1
    dut.in_spi_data.value = data

    await RisingEdge(dut.clk)
    # transaction done
    dut.in_spi_done.value = 1
    dut.in_spi_valid.value = 0
    dut.in_spi_data.value = 0   
    await RisingEdge(dut.clk)
    dut.in_spi_done.value = 0
    
async def timeout_monitor(dut):
    # all time coroutine to make sure it never hits timeout
    while True:
        await RisingEdge(dut.clk)
        if dut.rst_n.value == 0:
            continue
        assert dut.err_flag .value == 0, f"Timeout Triggered"

async def wr_sr(dut,exp_opcode:int,exp_data:int):
    # emualate write status reg,shift 2 byte out 
    await RisingEdge(dut.out_spi_valid)
    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 0
    # opcode
    got = int(dut.out_spi_data.value)
    assert got == exp_opcode, f"out_spi_data expected 0x{exp_opcode:#02x}, got {got:#04x}"
    # emulate shifting before 
    await spi_random_cycle(dut)
    # second handshake
    dut.in_spi_ready.value = 0
    await spi_random_cycle(dut)
    dut.in_spi_ready.value = 1
    await spi_random_cycle(dut)
    # data
    got = int(dut.out_spi_data.value)
    assert got == exp_data, f"out_spi_data expected 0x{exp_data:#08b}, got {got:#08b}"
    # transaction done
    dut.in_spi_done.value = 1
    await RisingEdge(dut.clk)
    dut.in_spi_done.value = 0   

# write data flow 
async def fsm_spi_output(dut, data, backpressure):
    i = 0
    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 0

    while i < len(data):
        if backpressure and random.randint(0, 1) == 0:
            dut.in_spi_ready.value = 0
        else:
            dut.in_spi_ready.value = 1

        await RisingEdge(dut.clk)

        if dut.in_spi_ready.value and dut.out_spi_valid.value:
            got = int(dut.out_spi_data.value)
            assert got == data[i], f"out_spi_data expect {data[i]:#02x} got {got:#02x}"
            i += 1

    dut._log.info(f"fsm_spi_output: all {len(data)} bytes received")

    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 1
    await RisingEdge(dut.clk)
    dut.in_spi_done.value  = 0

async def cu_fsm_input(dut, data, backpressure):
    dut.in_cu_valid.value = 0
    dut.in_cu_data.value  = 0

    for byte in data:
        while True:
            if backpressure and random.randint(0, 1) == 0:
                dut.in_cu_valid.value = 0
            else:
                dut.in_cu_valid.value = 1
                dut.in_cu_data.value  = byte

            await RisingEdge(dut.clk)
            if dut.in_cu_valid.value and dut.out_cu_ready.value:
                break

    dut.in_cu_valid.value = 0
    dut.in_cu_data.value  = 0

# read data flow
async def fsm_cu_output(dut,data,backpressure):
    # scoreboard for data flow from fsm to cu
    i =  0
    dut.in_cu_ready.value = 0
    while i < len(data):

        if backpressure and random.randint(0, 1) == 0:
            dut.in_cu_ready.value = 0
        else:
            dut.in_cu_ready.value = 1
        await RisingEdge(dut.clk)    

        if dut.out_cu_valid.value and dut.in_cu_ready.value:
            got = int(dut.out_cu_data.value)
            assert got == data[i], f"out_cu_data expect 0x{data[i]:02x} got 0x{got:02x}"
            i += 1
                
        # dut._log.info(
        # f"state={int(dut.state.value)}, "
        # f"total_bytes_left={int(dut.total_bytes_left.value)}" )     
    dut._log.info(f"fsm_spi_output: all {len(data)} bytes received")

    dut.in_cu_ready.value = 0

async def spi_fsm_input(dut,data,backpressure):
    # data input from cu to fsm (with back pressure)
    i = 0
    dut.in_spi_valid.value = 0
    dut.in_spi_data.value  = 0
    dut.in_spi_done.value  = 0
    for byte in data:
        # backpressure
        while backpressure and random.randint(0, 1) == 0:
            dut.in_spi_valid.value = 0
            await RisingEdge(dut.clk)

        dut.in_spi_valid.value = 1
        dut.in_spi_data.value  = byte


        while True:
            await RisingEdge(dut.clk)
            if dut.out_spi_ready.value:
                break

    dut.in_spi_valid.value = 0
    dut.in_spi_data.value  = 0
    dut.in_spi_done.value  = 1
    await RisingEdge(dut.clk)
    dut.in_spi_done.value  = 0   

# header send/check
async def header_send(dut,opcode,addr):
    # send opcode/addr to  fsm
    await spi_random_cycle(dut)
    while not int(dut.out_cu_ready.value):
        await RisingEdge(dut.clk)
    dut.in_cu_valid.value = 1
    dut.in_cu_data.value  = opcode
    dut.out_address.value = addr

    await RisingEdge(dut.clk)
    dut.in_cu_valid.value = 0

async def header_check(dut,opcode,addr):
    # check header coroutine
    dut.in_spi_ready.value = 0
    dut.in_spi_done.value  = 0
    # turn opcode and addr into a list
    header = [opcode,(addr >> 16) & 0xff, (addr>>8) & 0xff, addr & 0xff]
    i = 0
    while i < len(header):
        # always ready 
        dut.in_spi_ready.value = 1
        await RisingEdge(dut.clk)
        # out_spi_valid & in_spi_ready both high
        if int(dut.out_spi_valid.value):
            got = int(dut.out_spi_data.value)
            assert got == header[i], f"header[{i}] exp 0x{header[i]:02X}, got 0x{got:02X}"
            i += 1

    # done with header
    dut.in_spi_ready.value = 0    

async def wait_for_done(dut, timeout_cycles=1000):
    # wait for done signal
    for _ in range(timeout_cycles):
        if int(dut.in_fsm_done.value):
            return
        await RisingEdge(dut.clk)
    assert False, "in_fsm_done never asserted"

async def opcode_monitor(dut, opcode_log):
    """Runs forever, logging the first opcode byte of each SPI transaction."""
    while True:
        # Wait for transaction start
        await RisingEdge(dut.out_spi_valid)
        dut.in_spi_ready.value = 0
        dut.in_spi_done.value  = 0
        got = int(dut.out_spi_data.value)
        
        opcode_log.append(got)

@cocotb.test(timeout_time= 2000,timeout_unit='us')
async def fsm(dut):
    dut._log.info("FSM Start")
    
    # Set the clock period to 10 ns (100 MHz)
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await rst(dut)
    await write_flow(dut)
    await read_flow(dut)
    await invalid_opcode(dut)
    await read_flow_bp(dut)
    await write_flow_bp(dut)
    dut._log.info("FSM Pass")

async def rst(dut):
    dut._log.info("Reset start")


    dut.rst_n.value = 1
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 1
    timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
    # // CU
    # output wire out_cu_ready,
    # input wire in_cu_valid,
    # input wire [7:0] in_cu_data,

    # input wire in_cu_ready,
    # output reg out_cu_valid,
    # output reg [7:0] out_cu_data,

    # output reg in_fsm_done,
    
    # input wire out_fsm_enc_type,
    # input wire [1:0] out_fsm_opcode,
    # input wire [23:0] out_address,

    # // QSPI

    # //---- Transaction FSM connections ----
    # output reg in_start, //start the transaction
    # output reg r_w, //1 is read, 0 is write
    # output reg quad_enable, //0 use standard, 1 use quad
    # input wire in_spi_done, //tell the fsm we are done


    # //Send, MOSI side for write text commands
    # output reg out_spi_valid, //the fsm data is valid
    # output reg [7:0] out_spi_data, //the data to send to the flash
    # input wire in_spi_ready, //tells fsm controller is ready to send data

    # //Recv, MISO side for read key, read text commands
    # input wire in_spi_valid, //tell the fsm the out_data is valid
    # input wire [7:0] in_spi_data, //data to send to fsm
    # output wire out_spi_ready //fsm tells the controller it is ready to receive the data

    # fsm /bus data path emulating
    dut.in_cu_valid.value = 0
    dut.in_cu_data.value = 0
    dut.out_fsm_enc_type.value = 0
    dut.out_address.value = 0   
    dut.in_spi_done.value = 0
    dut.in_spi_ready.value = 1
    dut.in_spi_valid.value = 0   
    dut.in_spi_data.value = 0
    await RisingEdge(dut.clk)

    # reset output
    assert dut.out_spi_valid.value == 0,f"out_spi_valid expecpted 0 got {dut.out_spi_valid.value}"
    assert int(dut.out_spi_data.value) == 0,f"out_spi_data expecpted 0x00 got {int(dut.out_spi_data.value):#02x}" 

    assert dut.out_cu_valid.value == 0,f"out_cu_valid expecpted 0 got {dut.out_cu_valid.value}"
    assert int(dut.out_cu_data.value) == 0,f"out_cu_data expecpted 0x00 got {int(dut.out_cu_data.value):#02x}" 
    assert dut.in_start.value == 0,f"in_start expecpted 0 got {dut.in_start.value}"
    assert dut.r_w.value == 0,f"r_w expecpted 0 got {dut.r_w.value}"
    assert dut.quad_enable.value == 0,f"out_spi_valid expecpted 0 got {dut.quad_enable.value}"

    # start up flow starts
    # wren 
    await spi_wr(dut,0x06)

    # now wait for reset enable
    await spi_wr(dut,0x66)

    # wait for reset
    await spi_wr(dut,0x99)

    # wait for 30us expect sr1 poll
    await rd_sr(dut,0x05,0xff)
    await rd_sr(dut,0x05,0xff)
    await rd_sr(dut,0x05,0xff)
    await rd_sr(dut,0x05,0xf0)

    # wren + global unlock
    await spi_wr(dut,0x06)
    await spi_wr(dut,0x98)

    # wren+chip erase(with poll)
    await spi_wr(dut,0x06)
    await spi_wr(dut,0x60)

    # wip poll
    await rd_sr(dut,0x05,0xff)
    await RisingEdge(dut.clk)
    await rd_sr(dut,0x05,0xf0)

    #  read stuatus reg 2
    raw_sr2  = random.randint(0,255)
    raw_sr2  &= ~(1 << 1)   # clear bit[1]
    # process read status reg2 return data
    await rd_sr(dut,0x35,raw_sr2 )
    await spi_wr(dut,0x06) # wren
    # exp sr 2 to be shift out second bit be 1
    qe_sr2 = (raw_sr2 & ~(1 << 1)) | (1 << 1)
    # write to status reg 2
    await wr_sr(dut,0x31,qe_sr2)
    # check qe sent signal
    assert dut.qed.value == 1, f"qed expect 1 got {dut.qed.value}"
    # wip poll
    await rd_sr(dut,0x05,0xff)
    await RisingEdge(dut.clk)
    await rd_sr(dut,0x05,0xf0)

    dut._log.info("Reset Pass, Now in Normal Flow IDLE")    

async def write_flow(dut):
    # write flow without backpressure
    dut._log.info("Write Flow Start")
    async def wr_aes_no_bp():
        dut._log.info("Write AES Start")    
        opcode = wr_aes_generate_128b()
        addr = 0x123456
        data = [randomized_data() for _ in range(WR_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll + wren 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)

        await spi_wr(dut,0x06)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_PP,addr))
        await header_check_task
        # data flow
        data_check_task = cocotb.start_soon(fsm_spi_output(dut,data,0))
        await cu_fsm_input(dut,data,0)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Write AES Complete")

    async def wr_sha_no_bp():
        dut._log.info("Write SHA Start")
        opcode = wr_sha_generate_256b()
        addr = 0x123456
        data = [randomized_data() for _ in range(WR_SHA_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll + wren 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)

        await spi_wr(dut,0x06)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_PP,addr))
        await header_check_task
        # data flow
        data_check_task = cocotb.start_soon(fsm_spi_output(dut,data,0))
        await cu_fsm_input(dut,data,0)
        await data_check_task
         
        # done pulse
        await wait_for_done(dut)   
        dut._log.info("Write SHA Complete") 

    await wr_sha_no_bp()
    await wr_aes_no_bp()

    dut._log.info("Write Flow Pass")   

async def read_flow(dut):
    # read flow without backpressure
    dut._log.info("Read Flow Start")
    async def rd_txt_aes_no_bp():
        dut._log.info("Read Text AES Start")    
        opcode = rd_text_aes_128b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_TEXT_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,0))
        await spi_fsm_input(dut,data,0)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Text AES Complete")
    
    async def rd_txt_sha_no_bp():
        dut._log.info("Read Text SHA Start")    
        opcode = rd_text_sha_256b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_TEXT_SHA_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,0))
        await spi_fsm_input(dut,data,0)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Text SHA Complete")    

    async def rd_key_aes_no_bp():
        dut._log.info("Read Key AES Start")    
        opcode = rd_key_aes_256b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,0))
        await spi_fsm_input(dut,data,0)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Key AES Complete")

    await rd_txt_aes_no_bp()
    await rd_txt_sha_no_bp()
    await rd_key_aes_no_bp()
    dut._log.info("Read Flow Pass")

async def invalid_opcode(dut):
    # test invalid opcode
    dut._log.info("Invalid Opcode Start")   
    opcode = invalid()
    addr = 0x111111
    await header_send(dut,opcode,addr)  
    for _ in range(10):
        await RisingEdge(dut.clk)
        assert dut.out_spi_valid.value == 0, f"out_spi_valid expects 0 got {dut.out_spi_valid.value}"
        assert dut.in_start.value == 0, f"in_start expects 0 got {dut.in_start.value}"
    dut._log.info("Invalid Opcode Pass")

async def read_flow_bp(dut):
    # read flow with backpressure
    dut._log.info("Read Flow With Back Pressure Start")
    async def rd_txt_aes_bp():
        dut._log.info("Read Text Back Pressure AES Start")    
        opcode = rd_text_aes_128b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_TEXT_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,1))
        await spi_fsm_input(dut,data,1)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Text Back Pressure AES Complete")
    
    async def rd_txt_sha_bp():
        dut._log.info("Read Text Back Pressure SHA Start")    
        opcode = rd_text_sha_256b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_TEXT_SHA_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,1))
        await spi_fsm_input(dut,data,1)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Text Back Pressure SHA Complete")    

    async def rd_key_aes_bp():
        dut._log.info("Read Key Back Pressure AES Start")    
        opcode = rd_key_aes_256b()
        addr = 0xabcdef
        data = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_READ,addr))
        await header_check_task
        # dummy is read
        # 1  dummy
        await RisingEdge(dut.clk)
        assert dut.r_w.value == 1, f"r_w expect 1 got {dut.r_w.value}"
        dut.in_spi_valid.value = 0
        dut.in_spi_data.value = 0        
        await spi_random_cycle(dut)
        dut.in_spi_valid.value = 1
        await RisingEdge(dut.clk)
        # data flow
        data_check_task = cocotb.start_soon(fsm_cu_output(dut,data,1))
        await spi_fsm_input(dut,data,1)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Read Key Back Pressure AES Complete")

    await rd_txt_aes_bp()
    await rd_txt_sha_bp()
    await rd_key_aes_bp()
    dut._log.info("Read Flow With Back Pressure Pass")

async def write_flow_bp(dut):
    # write flow with backpressure
    dut._log.info("Write Flow With Back Pressure Start")
    async def wr_aes_bp():
        dut._log.info("Write AES With Back Pressure Start")    
        opcode = wr_aes_generate_128b()
        addr = 0x123456
        data = [randomized_data() for _ in range(WR_AES_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll + wren 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)

        await spi_wr(dut,0x06)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_PP,addr))
        await header_check_task
        # data flow
        data_check_task = cocotb.start_soon(fsm_spi_output(dut,data,1))
        await cu_fsm_input(dut,data,1)
        await data_check_task
        # done pulse
        await wait_for_done(dut)
        dut._log.info("Write AES With Back Pressure Complete")

    async def wr_sha_bp():
        dut._log.info("Write SHA With Back Pressure Start")
        opcode = wr_sha_generate_256b()
        addr = 0x123456
        data = [randomized_data() for _ in range(WR_SHA_BYTES)]
        # timeout coroutine
        timeout_check_task = cocotb.start_soon(timeout_monitor(dut))
        await header_send(dut,opcode,addr)
        # wip poll + wren 
        await rd_sr(dut,0x05,0xff)
        await RisingEdge(dut.clk)
        await rd_sr(dut,0x05,0xf0)

        await spi_wr(dut,0x06)
        
        header_check_task = cocotb.start_soon(header_check(dut,FLASH_PP,addr))
        await header_check_task
        # data flow
        data_check_task = cocotb.start_soon(fsm_spi_output(dut,data,1))
        await cu_fsm_input(dut,data,1)
        await data_check_task
         
        # done pulse
        await wait_for_done(dut)   
        dut._log.info("Write SHA With Back Pressure Complete") 

    await wr_sha_bp()
    await wr_aes_bp()

    dut._log.info("Write Flow With Back Pressure Pass")   
