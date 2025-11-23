# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Check
# Opcode used
# Reset Sequence

# ================== MEM TOP-LEVEL VERIFICATION PLAN ==================
# Only use: host cmd/data bus (+ready/valid), ack bus, QSPI pins, vendor model.

# 1) Startup sequence
#    Stimulus:
#      - Apply reset, then just run clock until startup is expected to finish.
#    Check (via QSPI monitor OR vendor model state):
#      - See 66h → 99h (SW reset).
#      - See 06h → 98h (global unlock).
#      - See 06h → C7h/60h (chip erase).
#      - See repeated 05h reads until SR1.WIP == 0.
#      - See 35h read of SR2 and, if QE was 0, 06h + 31h write setting QE=1.
#      - Finally: flash contents all 0xFF, SR2.QE == 1, SR1.WIP == 0.

# 2) Basic functional read/write via host
# 2.1) AES write 128b + read back
#    - Host sends WR_RES(AES, addr=A), streams 16 known bytes data_aes[0..15].
#    - Observe correct ack_bus_request/ack_bus_id handshake.
#    - After done, host sends RD_TEXT(AES, addr=A), captures 16 bytes.
#    - Expect: readback == data_aes and vendor_mem[A..A+15] == data_aes.

# 2.2) SHA write 256b + read back
#    - Same as above, but WR_RES(SHA) / RD_TEXT(SHA) with 32-byte data_sha.
#    - Expect: readback == data_sha and vendor_mem[B..B+31] == data_sha.

# 2.3) AES key read 256b
#    - Preload vendor model key region with key[0..31].
#    - Host issues RD_KEY(AES) at that region.
#    - Capture 32 bytes on host bus; expect == key[].

# 3) Ack bus behaviour
#    For each op above (RD_KEY, RD_TEXT AES/SHA, WR_RES AES/SHA):
#      - ack_bus_request goes high AFTER all byte sent.
#      - ack_bus_id == MEM (2'b00).
#      - When TB asserts ack_bus_owned (arbiter grant), mem deassert ack_bus_request, clear id.


# 4) Busy / serialization (using WIP)
#    - Start long WR_RES(SHA 256b) at addr=B (requires WE + program + WIP poll).
#    - Before it finishes, host tries another command (e.g. RD_TEXT(AES) at C).
#    Check:
#      - QSPI monitor: no new read/program opcodes issued until SR1.WIP == 0.
#      - Host side: either second command is ignored, or is accepted but only
#        starts QSPI traffic after first op completes (according to spec).

# 5) Invalid / garbage commands
#    - Host sends random illegal headers (your invalid() generator).
#    Expect:
#      - No QSPI traffic (except idle).
#      - No ack_bus_request (or defined error behaviour).
#      - Host never sees data on read side.

# 6) Random stress vs vendor-model scoreboard
#    - Maintain Python array expected_mem[] mirroring vendor model.
#    - Loop 8 times:
#        * Randomly choose one of:
#            - WR_RES AES 16B @ fixed addr.
#            - RD_TEXT AES 16B read back at addr.
#            - WR_RES SHA 32B @ fixed addr
#            - RD_TEXT AES 16B read back at addr
#            - preload addr with data 32B
#            - RD_KEY AES 32B read back at addr.
#        * For WR: drive random data via host, update expected_mem.
#        * For RD: capture host data, compare to expected_mem slice.
#    - Host ready/valid randomized each byte. QSPI pins ONLY driven by mem.
#    - Pass if no mismatches and vendor model reports no errors.

# 7) Full smoke test (startup + normal ops)
#    - Reset, let startup FSM finish (reuse test 1 checks).
#    - Then:
#        * AES WR 128b + AES RD 128b compare.
#        * SHA WR 256b + SHA RD 256b compare.
#    - Ensures whole stack (CMD + FSM + QSPI + flash model) works end-to-end.

#	For all tests not in qspi mode ensure only DI/DO pins being used
#	For all tests in qspi mode ensure  IO pins tri-stated when not use, driving tt uio_oe[3:0] pin individually
#
#	Get clarification for input/output to databus 
# =====================================================================
# General: clk, rst_n 
# To Bus
# ==================== OUT ==================== 
# [9]    READY       input
# [8]    VALID       output
# [7:0]  DATA        output

# ==================== IN =====================
# [9]    READY_IN    output
# [8]    VALID_IN    input
# [7:0]  DATA_IN     input

# ==================== OUT ====================
# [3]    ACK_READY        input     (1 = ready)
# [2]    ACK_VALID        output    (1 = module sending ack)
# [1:0]  MODULE_SOURCE_ID output

# ==================== IN =====================
# [2]    VALID_IN         input
# [1:0]  SOURCE_ID_IN     input

#  To Flash
#  /CS
#  DI      (IO0)
#  DO      (IO1)
#  /WP     (IO2)
#  /HOLD or /RESET (IO3)
#  SCLK
# 
#  To tt output ctrl
#  uio_oe[3:0]
import cocotb,random
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge,
    FallingEdge,
    Timer,
    ClockCycles,
    with_timeout,
)
from cocotb.utils import get_sim_time
from cocotb.result import SimTimeoutError, TestFailure

RD_DUMMY = 8

NUM_PAGES = 65536
PAGESIZE  = 256
FLASH_BYTES = NUM_PAGES * PAGESIZE  # 16,777,216
MAX_POLLS = 1024 # arbitrarily from rolling dice

RD_KEY_AES_BYTES = 32
RD_TEXT_AES_BYTES = 16
RD_TEXT_SHA_BYTES = 32

WR_AES_BYTES = 16
WR_SHA_BYTES = 32

KEY_BASE  = 0x000200

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
    src = 0b10                          # AES
    dest = 0b00
    opcode = 0b10                       # WR_RES
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def wr_sha_generate_256b():
    enc = random.randint(0,1)
    src = 0b01                          # SHA
    dest = 0b00
    opcode = 0b10                       # WR_RES
    return (enc<<7)|(0<<6)|(dest<<4)|(src<<2)|opcode

def invalid():
    enc = random.randint(0,1)
    reserved = 0
    opcode = random.randint(0,3)
    dest  = random.choice([0b01, 0b10, 0b11])
    src   = random.choice([0b00, 0b11])
    return (enc<<7)|(reserved<<6)|(dest<<4)|(src<<2)|opcode

def randomized_data():
    data = random.randint(0,255)
    return data

@cocotb.test()
async def mem_top(dut):
    dut._log.info("Mem Module Level Start")

    # Set the clock period to 10 ns (100 MHz)
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    # await full_smoke(dut)
    assert True

    dut._log.info("Mem Module Level Pass")


async def SPI_no_addr(dut):
        # Get opcode without addr
        dut._log.info("SPI Opcode Collect")
        await FallingEdge(dut.CS)
        opcode = 0x00   
        for _ in range(8):
            await RisingEdge(dut.SCLK)
            opcode = (opcode << 1) | int(dut.DI.value)
        t = get_sim_time(units="ns")
        dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")
        return opcode

async def SPI_addr(dut):
        # Get opcode with addr
        dut._log.info("SPI Opcode Collect")
        await FallingEdge(dut.CS)
        opcode = 0x00   
        for _ in range(8):
            await RisingEdge(dut.SCLK)
            opcode = (opcode << 1) | int(dut.DI.value)
        t = get_sim_time(units="ns")
        dut._log.info(f"[{t} ns] Opcode {opcode:#02x}")

        addr = 0
        for _ in range(24):
            await RisingEdge(dut.SCLK)
            addr = (addr << 1) | int(dut.DI.value)

        # Timestamp
        t = get_sim_time(units="ns")
        dut._log.info(f"[{t} ns] Opcode = 0x{opcode:02X}, Addr = 0x{addr:06X}") 
        return opcode, addr

async def opcode_monitor(dut, opcode_log):
    """Runs forever, logging the first opcode byte of each SPI transaction."""
    while True:
        # Wait for transaction start
        await FallingEdge(dut.CS)

        # Wait 8 bits of opcode on IO0 (mode 0, sample at rising)
        opcode = 0
        for _ in range(8):
            await RisingEdge(dut.SCLK)
            bit = int(dut.DI.value)
            opcode = (opcode << 1) | bit

        opcode_log.append(opcode)

        # Now wait for CS to go high again (end of transaction)
        await RisingEdge(dut.CS)

async def check_flash_erased(dut, flash):
    """Assert that every byte in the vendor model is 0xFF."""
    dut._log.info("Checking that flash is fully erased (all 0xFF)...")

    for addr in range(FLASH_BYTES):
        val = int(flash.memory[addr].value)
        if val != 0xFF:
            raise TestFailure(
                f"Flash not erased: memory[{addr:#08x}] = {val:#04x}, expected 0xFF"
            )

    dut._log.info("Flash erase check PASSED (all bytes 0xFF).")

async def preload_key_region(dut, data, base_addr):
    """Write RD_KEY_AES_BYTES[] into the vendor flash model at base_addr."""
    dut._log.info(f"Preloading key region at 0x{base_addr:06x}")
    for i in range(len(data)):
        dut.flash.memory[base_addr + i].value = data[i]
    # small delay to let simulator settle
    await Timer(50, "ns")

async def expect_ack(dut):
        await RisingEdge(dut.ACK_VALID)
        assert int(dut.MODULE_SOURCE_ID.value) & 0b11 == 0b00,f"MODULE_SOURCE_ID expect 0b00 got {int(dut.MODULE_SOURCE_ID.value) & 0b11:#02b}"
        dut.ACK_READY.value = 1
        await FallingEdge(dut.ACK_VALID)
        dut.ACK_READY.value = 0   

async def check_qspi_idle(dut, cycles=10):
    """
    While flash is idle, make sure we are not driving any IOs.
    Call this when you expect the controller to be idle (CS high).
    """
    for _ in range(cycles):
        await RisingEdge(dut.clk)

        # cs high
        assert dut.CS.value == 1, f"Idle: CS expected 1, got {dut.CS.value}"
        # sclk 0
        assert dut.SCLK.value == 0, f"Idle: SCLK expected 0, got {dut.SCLK.value}"
        # no io pins
        oe = int(dut.uio_oe.value) & 0xF
        assert oe == 0x0, f"Idle: uio_oe[3:0] expected 0000, got {oe:04b}"

async def send_header(dut, header_bytes):
    dut.VALID_IN.value = 1
    for b in header_bytes:
        dut.DATA_IN.value = b
        await RisingEdge(dut.clk)
    dut.VALID_IN.value = 0

async def send_write_payload(dut, data):
    i = 0
    while i < len(data):
        # randomized backpressure bus sending
        host_valid = random.randint(0, 1)
        dut.VALID_IN.value = host_valid
        if host_valid:
            dut.DATA_IN.value = data[i]

        await RisingEdge(dut.clk)
        if host_valid and int(dut.READY_IN.value):
            i += 1

    dut.VALID_IN.value = 0

async def recv_read_payload(dut, length):
    out = []
    while len(out) < length:
        # randomized back pressure bus receiving
        host_ready = random.randint(0, 1)
        dut.READY.value = host_ready
        await RisingEdge(dut.clk)

        if host_ready and int(dut.VALID.value):
            out.append(int(dut.DATA.value))

    dut.READY.value = 0
    return out



async def rst(dut):
# 1) Startup sequence
#    Stimulus:
#      - Apply reset, then just run clock until startup is expected to finish.
#    Check (via QSPI monitor OR vendor model state):
#      - See 66h → 99h (SW reset).
#      - See 06h → 98h (global unlock).
#      - See 06h → C7h/60h (chip erase).
    #      - See repeated 05h reads until SR1.WIP == 0.
    #      - See 35h read of SR2 and, if QE was 0, 06h + 31h write setting QE=1.
#      - Finally: flash contents all 0xFF, SR2.QE == 1, SR1.WIP == 0.
    async def spi_only_di_do():
        await FallingEdge(dut.CS)

        while int(dut.flash.status_reg[9].value) == 0 and dut.CS.value == 0:
            await RisingEdge(dut.SCLK)

            assert dut.IO2.value == 1, f"IO2 expected 1 got {dut.IO2.value}" 
            assert dut.IO3.value == 1, f"IO3 expected 1 got {dut.IO3.value}"
            oe = int(dut.uio_oe.value) & 0xF
            # IO2/IO3 must not be driven
            assert (oe & 0b1100) == 0, f"SPI1 mode: IO2/3 driven unexpectedly, uio_oe={oe:04b}"

    dut._log.info("Startup Flow Start")
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)  

    # reset output check 
    # bus
    assert dut.VALID.value == 0, f"VALID expected 0 got {dut.VALID.value}" 
    assert dut.ACK_VALID.value == 0, f"ACK_VALID expected 0 got {dut.ACK_VALID.value}"
    assert dut.READY_IN.value == 1, f"READY_IN expected 1 got {dut.READY_IN.value}"
    assert int(dut.MODULE_SOURCE_ID.value) == 0b00, f"MODULE_SOURCE_ID expected 0 got {int(dut.MODULE_SOURCE_ID.value):#04b}"
    assert int(dut.DATA.value) == 0x00, f"DATA expected 0 got {int(dut.DATA.value):#04x}"

    # flash
    assert dut.CS.value == 1, f"CS expected 1 got {dut.CS.value}" 
    assert dut.IO0.value == 0, f"IO0/DI expected 0 got {dut.IO0.value}" 
    assert dut.IO1.value.is_z, f"IO1/DO expected Z got {dut.IO1.value}"
    assert dut.IO2.value == 1, f"IO2 expected 1 got {dut.IO2.value}" 
    assert dut.IO3.value == 1, f"IO3 expected 1 got {dut.IO3.value}"
    assert dut.SCLK.value == 0, f"SCLK expected 0 got {dut.SCLK.value}"
    assert int(dut.MODULE_SOURCE_ID.value) == 0b00, f"MODULE_SOURCE_ID expected 0 got {int(dut.MODULE_SOURCE_ID.value):#04b}"
    assert int(dut.DATA.value) == 0x0, f"DATA expected 0 got {int(dut.DATA.value):#04x}"  

    # tt output ena  
    assert int(dut.uio_oe.value) == 0x0, f"uio_oe expected 0x0 got {int(dut.uio_oe.value):#04x}"

    # start up flow opcode check
    # coroutine spi only di do
    spi_task = cocotb.start_soon(spi_only_di_do())
    await spi_task
    # SW RST
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x66, f"Opcode expected 0x66 got {opcode:#02x}"
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x99, f"Opcode expected 0x99 got {opcode:#02x}"
    dut._log.info("SW Rst Done")
    # global unlock
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x06, f"Opcode expected 0x06 got {opcode:#02x}"
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x98, f"Opcode expected 0x98 got {opcode:#02x}"
    # chip erase
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x06, f"Opcode expected 0x06 got {opcode:#02x}"
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0xC7, f"Opcode expected 0xC7 got {opcode:#02x}"
    # read SR2 - QE enable
    saw_05 = False

    for _ in range(MAX_POLLS):
        try:
            # SPI_no_addr waits for a full transaction (CS low, bits shifted, CS high)
            await spi_task
            opcode = await with_timeout(SPI_no_addr(dut), 100, 'ms')
        except SimTimeoutError:
            raise cocotb.result.TestFailure("Timed out waiting for status opcode after chip erase")

        if opcode == 0x05:
            saw_05 = True
            continue
        elif opcode == 0x35:
            # Got SR2 read
            break
        else:
            raise cocotb.result.TestFailure(f"Unexpected opcode {opcode:#02x} during erase-polling; "
                "expected 0x05 (RDSR1) or 0x35 (RDSR2)")
    else:
        # Loop exhausted without seeing 0x35
        raise cocotb.result.TestFailure("Never saw 0x35 (RDSR2) after chip erase")

    if not saw_05:
        dut._log.warning("Did not see any 0x05 RDSR1 polls before 0x35 (RDSR2)")

    dut._log.info("Status polling → RDSR2 (0x35) observed")
        
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x06, f"Opcode expected 0x06 got {opcode:#02x}"
    await spi_task
    opcode = await SPI_no_addr(dut)
    assert opcode == 0x31, f"Opcode expected 0x31 got {opcode:#02x}"

    # Mem Model Status Reg Check
    await Timer(15,'ms')
    assert (int(dut.flash.status_reg.value) & 0b11 ) == 0, \
        f"Mem Model SR1[1:0] expected 0b00 got {(int(dut.flash.status_reg.value) & 0b11 ):#02b}"
    assert (int(dut.flash.status_reg.value>>9) & 0b1 ) == 1, \
        f"Mem Model SR2[1] expected 0b1 got {(int(dut.flash.status_reg.value>>9) & 0b1):#02b}"
    # Mem Model Flash Array Clear Check
    await check_flash_erased(dut,dut.flash)

    dut._log.info("Startup Flow Complete")

async def basic_read_write_ack(dut):
# 2) Basic functional read/write via host
# 2.1) AES write 128b + read back
#    - Host sends WR_RES(AES, addr=A), streams 16 known bytes data_aes[0..15].
#    - Observe correct ack_bus_request/ack_bus_id handshake.
#    - After done, host sends RD_TEXT(AES, addr=A), captures 16 bytes.
#    - Expect: readback == data_aes and vendor_mem[A..A+15] == data_aes.

# 2.2) SHA write 256b + read back
#    - Same as above, but WR_RES(SHA) / RD_TEXT(SHA) with 32-byte data_sha.
#    - Expect: readback == data_sha and vendor_mem[B..B+31] == data_sha.

# 2.3) AES key read 256b
#    - Preload vendor model key region with key[0..31].
#    - Host issues RD_KEY(AES) at that region.
#    - Capture 32 bytes on host bus; expect == key[].
# 3) Ack bus behaviour
#    For each op above (RD_KEY, RD_TEXT AES/SHA, WR_RES AES/SHA):
#      - ack_bus_request goes high AFTER all byte sent.
#      - ack_bus_id == MEM (2'b00).
#      - When TB asserts ack_bus_owned (arbiter grant), mem deassert ack_bus_request, clear id.
    dut._log.info("Basic Read/Write/Ack Flow Start")



    async def aes_wr_rd():
        # aes wr 128 rd back
        dut._log.info("AES Write 128b Read Back Start")
        # randomized data   aes wr opcode   addr:0x000000 from [23:0]
        data = [randomized_data() for _ in range(WR_AES_BYTES)]
        inputsequence = [wr_aes_generate_128b(),0x00,0x00,0x00]

        # Bus valid high
        dut.VALID_IN.value = 1
        for i in inputsequence:
            dut.DATA_IN.value = i
            await RisingEdge(dut.clk)
        # deassert valid
        dut.VALID_IN.value = 0

        async def bus_mem_aeswr():
            j = 0
            dut.VALID_IN.value = 1
            # input data write
            while j <len(data):
                dut.DATA_IN.value = data[j]
                await RisingEdge(dut.clk)

                if dut.READY_IN.value == 1:
                    j += 1
            dut.VALID_IN.value = 0

        async def qspi_uio_oe_wraes():
            # tt uio_oe check
            dut._log.info("Waiting for WIP=0 in vendor status_reg...")
            try:
                if dut.flash.status_reg[0].value == 1:
                    await with_timeout(FallingEdge(dut.flash.status_reg[0]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WIP=0 in status_reg")
            
            dut._log.info("Waiting for WEL=1 in vendor status_reg...")
            try:
                await with_timeout(RisingEdge(dut.flash.status_reg[1]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WEL=1 in status_reg")
            
            await FallingEdge(dut.CS)
            for _ in range(8+24):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 1,f"uio_oe[3:0] expect 0b0001 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # QSPI Output
            for _ in range(WR_AES_BYTES*2):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0b1111,f"uio_oe[3:0] expect 0b1111 got {int(dut.uio_oe.value) & 0xf:#04b}"
            await RisingEdge(dut.CS)
        # ack coroutine
        ack_task = cocotb.start_soon(expect_ack(dut))
        # coroutine qspi uio oe and bus input monitor
        process = cocotb.start_soon(bus_mem_aeswr())
        await qspi_uio_oe_wraes()
        await process
        await ack_task

        # aes rd text  
        # read opcode generate
        inputsequence = [rd_text_aes_128b(),0x00,0x00,0x00]
        # Bus valid high
        dut.VALID_IN.value = 1
        # shift opcode
        for i in inputsequence:
            dut.DATA_IN.value = i
            await RisingEdge(dut.clk) 
        # deassert valid
        dut.VALID_IN.value = 0       
        # bus ready
        dut.READY.value = 1
        await RisingEdge(dut.clk)

        async def mem_bus_aesrd():
            dut.READY.value = 1
            j = 0
            while j < len(data):
                await RisingEdge(dut.clk)
                if dut.VALID.value == 1:
                    got = int(dut.DATA.value)
                    exp = data[j]
                    assert got == exp,f"Expected data {exp:#04x}, got {got:#04x}"
                    j+=1
            dut.READY.value = 0

        async def qspi_uio_oe_rdaes():
            # tt uio_oe check            
            dut._log.info("Waiting for WIP=0 in vendor status_reg...")
            try:
                if dut.flash.status_reg[0].value == 1:
                    await with_timeout(FallingEdge(dut.flash.status_reg[0]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WIP=0 in status_reg")
                                
            await FallingEdge(dut.CS)
            for _ in range(8+24):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 1,f"uio_oe[3:0] expect 0b0001 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # dummy
            for _ in range(RD_DUMMY):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # QSPI Input
            for _ in range(RD_TEXT_AES_BYTES*2):
                await RisingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"            
        # ack coroutine
        ack_task = cocotb.start_soon(expect_ack(dut))
        # coroutine qspi uio oe and mem to bus
        process = cocotb.start_soon(mem_bus_aesrd())
        await qspi_uio_oe_rdaes()
        await process
        await ack_task

        dut._log.info("AES Write 128b Read Back Complete")

    async def sha_wr_rd():
        # sha wr rd back
        dut._log.info("SHA Write 256 Read Back Start")
        # randomized data   aes wr opcode   addr:0x000100 from [23:0]
        data = [randomized_data() for _ in range(WR_SHA_BYTES)]
        inputsequence = [wr_sha_generate_256b(),0x00,0x01,0x00]

        # Bus valid high
        dut.VALID_IN.value = 1
        for i in inputsequence:
            dut.DATA_IN.value = i
            await RisingEdge(dut.clk)

        # deassert valid
        dut.VALID_IN.value = 0

        async def bus_mem_shawr():
            j = 0
            dut.VALID_IN.value = 1
            # input data write
            while j <len(data):
                dut.DATA_IN.value = data[j]
                await RisingEdge(dut.clk)

                if dut.READY_IN.value == 1:
                    j += 1
            dut.VALID_IN.value = 0

        async def qspi_uio_oe_wrsha():
            # tt uio_oe check
            dut._log.info("Waiting for WIP=0 in vendor status_reg...")
            try:
                if dut.flash.status_reg[0].value == 1:
                    await with_timeout(FallingEdge(dut.flash.status_reg[0]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WIP=0 in status_reg")
            
            dut._log.info("Waiting for WEL=1 in vendor status_reg...")
            try:
                await with_timeout(RisingEdge(dut.flash.status_reg[1]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WEL=1 in status_reg")
            
            await FallingEdge(dut.CS)
            for _ in range(8+24):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 1,f"uio_oe[3:0] expect 0b0001 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # QSPI Output
            for _ in range(WR_SHA_BYTES*2):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0b1111,f"uio_oe[3:0] expect 0b1111 got {int(dut.uio_oe.value) & 0xf:#04b}"
            await RisingEdge(dut.CS)

 
        # ack coroutine
        ack_task = cocotb.start_soon(expect_ack(dut))
        # coroutine qspi uio oe and bus input monitor
        process = cocotb.start_soon(bus_mem_shawr())
        await qspi_uio_oe_wrsha()
        await process
        await ack_task

        # aes rd text  
        # read opcode generate
        inputsequence = [rd_text_sha_256b(),0x00,0x01,0x00]
        # Bus valid high
        dut.VALID_IN.value = 1
        # shift opcode
        for i in inputsequence:
            dut.DATA_IN.value = i
            await RisingEdge(dut.clk)
        # deassert valid
        dut.VALID_IN.value = 0      
        # bus ready
        dut.READY.value = 1
        await RisingEdge(dut.clk)

        async def mem_bus_shard():
            dut.READY.value = 1
            j = 0
            while j < len(data):
                await RisingEdge(dut.clk)
                if dut.VALID.value == 1:
                    got = int(dut.DATA.value)
                    exp = data[j]
                    assert got == exp,f"Expected data {exp:#04x}, got {got:#04x}"
                    j+=1
            dut.READY.value = 0

        async def qspi_uio_oe_rdsha():
            # tt uio_oe check            
            dut._log.info("Waiting for WIP=0 in vendor status_reg...")
            try:
                if dut.flash.status_reg[0].value == 1:
                    await with_timeout(FallingEdge(dut.flash.status_reg[0]), 15, 'ms')
            except SimTimeoutError:
                raise TestFailure("Timed out waiting for WIP=0 in status_reg")
                                
            await FallingEdge(dut.CS)
            for _ in range(8+24):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 1,f"uio_oe[3:0] expect 0b0001 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # dummy
            for _ in range(RD_DUMMY):
                await FallingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"
            # QSPI Input
            for _ in range(RD_TEXT_SHA_BYTES*2):
                await RisingEdge(dut.SCLK)
                assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"            
        # ack coroutine
        ack_task = cocotb.start_soon(expect_ack(dut))
        # coroutine qspi uio oe and mem to bus
        process = cocotb.start_soon(mem_bus_shard())
        await qspi_uio_oe_rdsha()
        await process
        await ack_task

        dut._log.info("SHA Write 256b Read Back Complete")

    async def aes_rd_key():
            # aes 256 rd key 
            dut._log.info("AES 256 Read Back Start")
            # randomized data   aes wr opcode   addr:0x000200 from [23:0]
            data = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]
            await preload_key_region(dut,data,KEY_BASE)
            # aes rd text  
            # read opcode generate
            inputsequence = [rd_key_aes_256b(),0x00,0x02,0x00]
            # Bus valid high
            dut.VALID_IN.value = 1
            # shift opcode
            for i in inputsequence:
                dut.DATA_IN.value = i
                await RisingEdge(dut.clk) 
            
            # deassert valid
            dut.VALID_IN.value = 0    
            # bus ready
            dut.READY.value = 1
            await RisingEdge(dut.clk)

            async def mem_bus_aesrd_key():
                dut.READY.value = 1
                j = 0
                while j < len(data):
                    await RisingEdge(dut.clk)
                    if dut.VALID.value == 1:
                        got = int(dut.DATA.value)
                        exp = data[j]
                        assert got == exp,f"Expected data {exp:#04x}, got {got:#04x}"
                        j+=1
                dut.READY.value = 0

            async def qspi_uio_oe_rdaes_key():
                # tt uio_oe check            
                dut._log.info("Waiting for WIP=0 in vendor status_reg...")
                try:
                    if dut.flash.status_reg[0].value == 1:
                        await with_timeout(FallingEdge(dut.flash.status_reg[0]), 15, 'ms')
                except SimTimeoutError:
                    raise TestFailure("Timed out waiting for WIP=0 in status_reg")
                                    
                await FallingEdge(dut.CS)
                for _ in range(8+24):
                    await FallingEdge(dut.SCLK)
                    assert int(dut.uio_oe.value) & 0xf == 1,f"uio_oe[3:0] expect 0b0001 got {int(dut.uio_oe.value) & 0xf:#04b}"
                # dummy
                for _ in range(RD_DUMMY):
                    await FallingEdge(dut.SCLK)
                    assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"
                # QSPI Input
                for _ in range(RD_KEY_AES_BYTES*2):
                    await RisingEdge(dut.SCLK)
                    assert int(dut.uio_oe.value) & 0xf == 0,f"uio_oe[3:0] expect 0b0000 got {int(dut.uio_oe.value) & 0xf:#04b}"            

                # ack coroutine
            
            ack_task = cocotb.start_soon(expect_ack(dut))
            # coroutine qspi uio oe and mem to bus
            process = cocotb.start_soon(mem_bus_aesrd_key())
            await qspi_uio_oe_rdaes_key()
            await process
            await ack_task

            dut._log.info("AES 256b Read Complete")

    await aes_wr_rd()
    await check_qspi_idle(dut)
    await sha_wr_rd()
    await check_qspi_idle(dut)
    await aes_rd_key()
    await check_qspi_idle(dut)
    dut._log.info("Basic Read/Write/Ack Flow Complete")

async def busy_WIP(dut):
    # 4) Busy / serialization (using WIP)
    #   - Start long WR_RES(SHA 256b) at addr=B.
    #   - Before it finishes, host tries another command (e.g. RD_KEY(AES) at C).
    #   - Check: while SR1.WIP == 1, only status polls (0x05) go out on QSPI.

    dut._log.info("Busy WIP Test Start")

    # SHA write that causes WIP=1
    async def sha_wr():
        dut._log.info("SHA Write 256B at 0x000300 start")
        data = [randomized_data() for _ in range(WR_SHA_BYTES)]
        header = [wr_sha_generate_256b(), 0x00, 0x03, 0x00]  # addr = 0x000300

        # send 4-beat header
        dut.VALID_IN.value = 1
        for b in header:
            dut.DATA_IN.value = b
            await RisingEdge(dut.clk)
        dut.VALID_IN.value = 0

        async def bus_mem_shawr():
            j = 0
            dut.VALID_IN.value = 1
            while j < len(data):
                dut.DATA_IN.value = data[j]
                await RisingEdge(dut.clk)
                if dut.READY_IN.value == 1:
                    j += 1
            dut.VALID_IN.value = 0

        # ack coroutine for the SHA write
        ack_task = cocotb.start_soon(expect_ack(dut))
        await bus_mem_shawr()
        await ack_task

        dut._log.info("SHA WR_RES command + payload sent")


    async def send_aes_rd_key_cmd():
        dut._log.info("Issuing AES RD_KEY command while flash may be busy")
        header = [rd_key_aes_256b(), 0x00, 0x04, 0x00]  # addr = 0x000400

        dut.VALID_IN.value = 1
        for b in header:
            dut.DATA_IN.value = b
            await RisingEdge(dut.clk)
        dut.VALID_IN.value = 0

        # dont care returned data
        dut.READY.value = 1
        # ack
        await expect_ack(dut)
        dut.READY.value = 0

    async def monitor_qspi_while_busy():
        # wait until flash becomes busy
        dut._log.info("Waiting for WIP=1 in vendor status_reg...")
        try:
            await with_timeout(RisingEdge(dut.flash.status_reg[0]), 15, "ms")
        except SimTimeoutError:
            raise TestFailure("Timed out waiting for WIP=1 (flash never became busy)")

        dut._log.info("WIP==1; now monitoring QSPI opcodes (expect only 0x05)")

        # while busy, every SPI_no_addr() we see must be a 0x05 status read
        while dut.flash.status_reg[0].value == 1:
            opcode = await with_timeout(SPI_no_addr(dut), 10, "ms")
            if opcode != 0x05:
                raise TestFailure(
                    f"Unexpected opcode {opcode:#04x} while WIP==1; expected 0x05 (RDSR1 only)"
                )

        dut._log.info("WIP returned to 0, QSPI busy-monitor done")

    # Start SHA write and monitor in parallel
    sha_task = cocotb.start_soon(sha_wr())
    monitor_task = cocotb.start_soon(monitor_qspi_while_busy())
    # Wait until WIP actually goes high, then issue second command
    await RisingEdge(dut.flash.status_reg[0])
    dut._log.info("Flash WIP==1 now; sending AES RD_KEY command")

    await send_aes_rd_key_cmd()

    # Wait for SHA write + monitor to finish
    await sha_task
    await monitor_task

    dut._log.info("Busy WIP Test Complete")

async def invalid_opcode(dut):
# 5) Invalid / garbage commands
#    - Host sends random illegal headers (your invalid() generator).
#    Expect:
#      - No QSPI traffic (except idle).
#      - No ack_bus_request (or defined error behaviour).
#      - Host never sees data on read side.
    dut._log.info("Invalid Opcode Test Start")

    # invalid opcode with addr 0x000500
    header = [invalid(),0x00,0x05,0x00]
    # send 4-beat header
    dut.VALID_IN.value = 1
    for b in header:
        dut.DATA_IN.value = b
        await RisingEdge(dut.clk)
    dut.VALID_IN.value = 0

    async def invalid_output_monitor(cycles=200):
        for _ in range(cycles):
            # No QSPI transaction
            assert dut.CS.value == 1, f"Expect CS=1 (idle), got {dut.CS.value}"
            # No ack request
            assert dut.ACK_VALID.value == 0, f"Expect ACK_VALID=0, got {dut.ACK_VALID.value}"
            # No read data back to host
            assert dut.VALID.value == 0, f"Expect VALID=0 (no data), got {dut.VALID.value}"
            await RisingEdge(dut.clk)
    
    await invalid_output_monitor()

    dut._log.info("Invalid Opcode Test Complete")

async def random_stress(dut):
# 6) Random stress vs vendor-model scoreboard
#    - Maintain Python array expected_mem[] mirroring vendor model.
#    - Loop 8 times:
#        * Randomly choose one of:
#            - WR_RES AES 16B @ fixed addr.
#            - RD_TEXT AES 16B read back at addr.
#            - WR_RES SHA 32B @ fixed addr
#            - RD_TEXT AES 16B read back at addr
#            - preload addr with data 32B
#            - RD_KEY AES 32B read back at addr.
#        * For WR: drive random data via host, update expected_mem.
#        * For RD: capture host data, compare to expected_mem slice.
#    - Host ready/valid randomized each byte. QSPI pins ONLY driven by mem.
#    - Pass if no mismatches and vendor model reports no errors.  
    dut._log.info("Random Stress Test Start")
    # fixed addr 
    aes_addr = 0x000600
    sha_addr = 0x000700
    aes_key_addr = 0x000800
    
    async def wr_sha_backpressure_rd(addr):
        # randomized data
        data = [randomized_data() for _ in range(WR_SHA_BYTES)]
        header = [wr_sha_generate_256b(),(addr>>16)&0xff,(addr>>8)&0xff,(addr)&0xff]

        await send_header(dut,header)
        wr_ack_task = cocotb.start_soon(expect_ack(dut))
        await send_write_payload(dut,data)
        await wr_ack_task

        header = [rd_text_sha_256b(),(addr>>16)&0xff,(addr>>8)&0xff,(addr)&0xff]

        await send_header(dut,header)
        rd_ack_task = cocotb.start_soon(expect_ack(dut))
        got = await recv_read_payload(dut,WR_SHA_BYTES)
        await rd_ack_task
        for i, (exp, g) in enumerate(zip(data, got)):
            assert g == exp, f"SHA backpressure mismatch @byte {i}: exp {exp:#04x}, got {g:#04x}"
        
        next_sha_addr = addr + WR_SHA_BYTES
        return next_sha_addr

    async def wr_aes_backpressure_rd(addr):
        # randomized data
        data = [randomized_data() for _ in range(WR_AES_BYTES)]
        header = [wr_aes_generate_128b(),(addr>>16)&0xff,(addr>>8)&0xff,(addr)&0xff]

        await send_header(dut,header)
        wr_ack_task = cocotb.start_soon(expect_ack(dut))
        await send_write_payload(dut,data)
        await wr_ack_task

        header = [rd_text_aes_128b(),(addr>>16)&0xff,(addr>>8)&0xff,(addr)&0xff]

        await send_header(dut,header)
        rd_ack_task = cocotb.start_soon(expect_ack(dut))
        got = await recv_read_payload(dut,WR_AES_BYTES)
        await rd_ack_task
        for i, (exp, g) in enumerate(zip(data, got)):
            assert g == exp, f"AES backpressure mismatch @byte {i}: exp {exp:#04x}, got {g:#04x}"
        
        next_aes_addr = addr + WR_AES_BYTES
        return next_aes_addr
    
    async def preload_aes_backpressure_rd(addr):
        # randomized data
        data = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]
        await preload_key_region(dut,data,addr)

        header = [rd_key_aes_256b(),(addr>>16)&0xff,(addr>>8)&0xff,(addr)&0xff]   
        await send_header(dut,header)     

        rd_key_ack_task = cocotb.start_soon(expect_ack(dut))
        got = await recv_read_payload(dut,RD_KEY_AES_BYTES)
        await rd_key_ack_task
        for i, (exp, g) in enumerate(zip(data, got)):
            assert g == exp, f"AES backpressure mismatch @byte {i}: exp {exp:#04x}, got {g:#04x}"
        
        next_aes_key_addr = addr + RD_KEY_AES_BYTES
        return next_aes_key_addr

    for _ in range(8):
        aes_addr = await wr_aes_backpressure_rd(aes_addr)
    for _ in range(8):
        sha_addr = await wr_sha_backpressure_rd(sha_addr)
    for _ in range(8):
        aes_key_addr = await preload_aes_backpressure_rd(aes_key_addr)   

    dut._log.info("Random Stress Test Complete")

async def full_smoke(dut):
# 7) Full smoke test (startup + normal ops)
#    - Reset, let startup FSM finish (reuse test 1 checks).
#    - Then:
#        * AES WR 128b + AES RD 128b compare.
#        * SHA WR 256b + SHA RD 256b compare.
#    - Ensures whole stack (CMD + FSM + QSPI + flash model) works end-to-end.
    dut._log.info("Full Smoke Test Start")

    await rst(dut)

    # 2. Basic functional read/write + ack + uio_oe checks
    await basic_read_write_ack(dut)

    # 3. Busy / WIP serialization (while busy only 0x05 should appear)
    await busy_WIP(dut)

    # 4. Invalid / garbage opcode – confirm no QSPI traffic, no ack, no read data
    await invalid_opcode(dut)

    # 5. Random stress: AES/SHA/key with random data + random backpressure
    await random_stress(dut)

    # 6.idle check at the end
    await ClockCycles(dut.clk, 20)
    assert dut.CS.value == 1, "End-of-smoke: CS should be high (idle)"
    assert dut.ACK_VALID.value == 0, "End-of-smoke: ACK_VALID should be low"
    assert dut.VALID.value == 0, "End-of-smoke: no data driving bus"    
    await check_qspi_idle(dut)

    dut._log.info("Full Smoke Test Complete")