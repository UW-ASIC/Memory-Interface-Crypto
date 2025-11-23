# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Clarification required on: 

# data bus control timing

    # input wire clk,
    # input wire rst_n,

    # // --- Bus ---
    # input wire in_bus_valid,
    # input wire [7:0] in_bus_data,
    # output reg out_bus_ready,

    # input wire in_bus_ready,
    # output reg [7:0] out_bus_data,
    # output reg out_bus_valid,
    
    # // --- Ack Bus ---
    # input wire in_ack_bus_owned,
    # output reg out_ack_bus_request,
    # output reg [1:0] out_ack_bus_id,

    # // --- Transaction FSM ---
    # input wire in_fsm_ready,
    # output wire out_to_fsm_valid;
    # output reg [7:0] out_fsm_data,


    # output wire out_to_fsm_ready;
    # input wire in_fsm_valid,
    # input wire [7:0] in_fsm_data,
    
    # output wire out_fsm_enc_type,

import cocotb,random
from cocotb.clock import Clock
from cocotb.triggers import (
    RisingEdge,
    FallingEdge,
    Timer,
    ClockCycles,
    with_timeout,
    SimTimeoutError,
)
from cocotb.utils import get_sim_time

RD_KEY_AES_BYTES = 32
RD_TEXT_AES_BYTES = 16
RD_TEXT_SHA_BYTES = 32

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
async def mem_cu(dut):

    dut._log.info("CMD Submodule Start")
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await rst(dut)
    # await do_test_rd_key_decode(dut)
    # await do_test_rd_text_decode(dut)
    # await do_test_wr_res_decode(dut)
    await do_test_invalid_header(dut)
    await do_test_read_from_bus(dut)
    await do_test_write_to_bus(dut)
    await do_test_fsm_handshake(dut)
    dut._log.info("CMD Submodule Complete")
    
async def header_send(dut,header):
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i in header:
        dut.in_bus_data.value = i
        await RisingEdge(dut.clk)

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0

async def rst(dut):
    #reset check all output port
    dut._log.info("Reset start")
    dut.rst_n.value = 1
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk,5)
    dut.rst_n.value = 1

    # fsm /bus data path emulating
    dut.in_ack_bus_owned.value = 0
    dut.in_bus_ready.value = 0
    dut.in_bus_valid.value = 0
    dut.in_fsm_valid.value = 0   
    dut.in_fsm_ready.value = 1
    await RisingEdge(dut.clk)

    # // --- Transaction FSM ---
    # input wire in_fsm_ready,
    # output wire out_to_fsm_valid;
    # output reg [7:0] out_fsm_data,


    # output wire out_to_fsm_ready;
    # input wire in_fsm_valid,
    # input wire [7:0] in_fsm_data,

    assert dut.out_to_fsm_valid.value == 0,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
    assert dut.out_to_fsm_ready.value == 0,f"out_to_fsm_ready expecpted 0 got {dut.out_to_fsm_ready.value}"
    # // --- Bus ---
    # input wire in_bus_valid,
    # input wire [7:0] in_bus_data,
    # output reg out_bus_ready, 
    
    # input wire in_bus_ready,
    # output reg [7:0] out_bus_data,
    # output reg out_bus_valid,

    assert dut.out_bus_ready.value == 1,f"out_bus_ready expecpted 1 got {dut.out_bus_ready.value}"
    assert dut.out_bus_valid.value == 0,f"out_bus_valid expecpted 0 got {dut.out_bus_valid.value}"

        # // --- Ack Bus ---
    # input wire in_ack_bus_owned,
    # output reg out_ack_bus_request,
    # output reg [1:0] out_ack_bus_id,
    assert dut.out_ack_bus_request.value == 0,f"out_ack_bus_request expecpted 1 got {dut.out_ack_bus_request.value}"
    assert int(dut.out_ack_bus_id.value) == 0,f"out_ack_bus_id expecpted 0b00 got {int(dut.out_ack_bus_id.value):#02b}"  

    dut._log.info("Reset complete")
    

async def do_test_valid_header(dut):
    # invalid opcode: check ena signal, valid signal
    await rst(dut)
    dut._log.info("Valid Hearder start")
    await ClockCycles(dut.clk,5)
    # valid header addr from 0x654321
    header = [rd_key_aes_256b(),0x21,0x43,0x65]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)
        assert dut.out_to_fsm_valid.value == 1,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
        assert int(dut.out_fsm_data.value) == header[i],f"out_fsm_data expecpted {header[i]} got {int(dut.out_fsm_data.value):#04x}"

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk)

    await rst(dut)
    await ClockCycles(dut.clk,5)
    # valid header addr from 0x563412
    header = [rd_text_aes_128b(),0x12,0x34,0x56]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)
        assert dut.out_to_fsm_valid.value == 1,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
        assert int(dut.out_fsm_data.value) == header[i],f"out_fsm_data expecpted {header[i]} got {int(dut.out_fsm_data.value):#04x}"

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk)

    await rst(dut)
    await ClockCycles(dut.clk,5)
    # valid header addr from 0xfedcba
    header = [rd_text_sha_256b(),0xba,0xdc,0xfe]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)
        assert dut.out_to_fsm_valid.value == 1,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
        assert int(dut.out_fsm_data.value) == header[i],f"out_fsm_data expecpted {header[i]} got {int(dut.out_fsm_data.value):#04x}"

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk)

    await rst(dut)
    await ClockCycles(dut.clk,5)
    header = [wr_aes_generate_128b(),0x21,0x43,0x65]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)
        assert dut.out_to_fsm_valid.value == 1,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
        assert int(dut.out_fsm_data.value) == header[i],f"out_fsm_data expecpted {header[i]} got {int(dut.out_fsm_data.value):#04x}"

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk) 

    await rst(dut)
    await ClockCycles(dut.clk,5)
    header = [wr_sha_generate_256b(),0x21,0x43,0x65]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)
        assert dut.out_to_fsm_valid.value == 1,f"out_to_fsm_valid expecpted 1 got {dut.out_to_fsm_valid.value}"
        assert int(dut.out_fsm_data.value) == header[i],f"out_fsm_data expecpted {header[i]} got {int(dut.out_fsm_data.value):#04x}"

    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk)    
    dut._log.info("Valid Hearder Complete")  

async def do_test_invalid_header(dut):
    # invalid opcode: check ena signal, valid signal
    await rst(dut)
    dut._log.info("Invalid Hearder start")   
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.bus_valid.value = 1 

    for _ in range(10):
        #invalid opcode, and address 0xfedcba from 23:0
    # invalid opcode: check ena signal, valid signal

        # invalid header addr from 0x654321
        header = [invalid(),0x21,0x43,0x65]
        dut.in_bus_valid.value = 1
        dut.in_fsm_ready.value = 1
        for i,b in enumerate(header):
            dut.in_bus_data.value = b
            await RisingEdge(dut.clk)
            assert dut.out_to_fsm_valid.value == 0,f"out_to_fsm_valid expecpted 0 got {dut.out_to_fsm_valid.value}"
            assert int(dut.out_fsm_data.value) == 0x00,f"out_fsm_data expecpted {0x00} got {int(dut.out_fsm_data.value):#04x}"

        dut.in_bus_valid.value = 0
        dut.in_fsm_ready.value = 0
        dut.in_fsm_ready.value = 1
        # wait cu to process
        await RisingEdge(dut.clk)  
             
    dut._log.info("Invalid Hearder comeplete")

async def do_test_read_from_bus(dut):
    # read flow test with backpressure from fsm/bus
    await rst(dut)
    dut._log.info("Read Flow start")   
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.in_bus_valid.value = 1
    
    # read text back pressure
    async def rdkey():
        dut._log.info("Read Key Start")
        # read key randomized data 32 Bytes
        rd_key = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]

        # read key randomized opcode, and address 0xfedcba from 23:0
        rd_keyarr = [rd_key_aes_256b(),0xBA, 0xDC, 0xFE]

        dut.in_bus_valid.value = 1
        for i in rd_keyarr:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
            
        # deassert bus calid
        dut.in_bus_valid.value = 0
        dut.in_bus_ready.value = 0
        # pull down ready on bus     
        await RisingEdge(dut.clk)

        
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1
        # check rd key data matching with randomized back pressure
        async def fsm_cu_rdkey():
            # read flow fsm to cu backpressure
            i = 0
            await RisingEdge(dut.clk)
            while i<len(rd_key):
                dut.in_fsm_data.value = rd_key[i]
                dut.in_fsm_valid.value = random.randint(0,1)

                await RisingEdge(dut.clk)
                if dut.in_fsm_valid.value == 1 and int(dut.out_to_fsm_ready.value) == 1:
                    i += 1

            dut.in_fsm_valid.value = 0
        async def cu_bus_rdkey():
            # read flow from cu to bus
            j = 0
            await RisingEdge(dut.clk)
            while j<len(rd_key):
                dut.in_bus_ready.value = random.randint(0,1)
                await RisingEdge(dut.clk)
                if int(dut.out_bus_valid.value) == 1 and dut.in_bus_ready.value == 1:
                    got = int(dut.out_bus_data.value)
                    exp = rd_key[j]
                    assert got == exp,f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j+=1

            dut.in_bus_ready.value = 1
            
        producer_rdkey = cocotb.start_soon(fsm_cu_rdkey())
        await cu_bus_rdkey()
        await producer_rdkey
        dut._log.info("Read Key pass")

    async def rdtxt_aes():
        dut._log.info("Read Text AES start")
        # read text randomized data 16 Bytes
        rd_txt = [randomized_data() for _ in range(RD_TEXT_AES_BYTES)]
        # read text opcode with randomized opcode, and address 0x654321 
        rd_txtarr = [rd_text_aes_128b(),0x21, 0x43, 0x65]

        dut.in_bus_valid.value = 1
        for i in rd_txtarr:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        # deassert bus calid
        dut.in_bus_valid.value = 0
        # pull down ready on bus until rise edge of ena     
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 0
        
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1
        # check rd text data matching with randomized back pressure
        async def fsm_cu_rdtxt_aes():
            # read flow fsm to cu backpressure
            i = 0
            await RisingEdge(dut.clk)
            while i<len(rd_txt):
                dut.in_fsm_data.value = rd_txt[i]
                dut.in_fsm_valid.value = random.randint(0,1)

                await RisingEdge(dut.clk)
                if dut.in_fsm_valid.value == 1 and int(dut.out_to_fsm_ready.value) == 1:
                    i += 1

            dut.in_fsm_valid.value = 0
        async def cu_bus_rdtxt_aes():
            # read flow from cu to bus
            j = 0
            await RisingEdge(dut.clk)
            while j<len(rd_txt):
                dut.in_bus_ready.value = random.randint(0,1)
                await RisingEdge(dut.clk)
                if int(dut.out_bus_valid.value) == 1 and dut.in_bus_ready.value == 1:
                    got = int(dut.out_bus_data.value)
                    exp = rd_txt[j]
                    assert got == exp,f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j+=1

            dut.in_bus_ready.value = 1
            
        producer_rdtxt = cocotb.start_soon(fsm_cu_rdtxt_aes())
        await cu_bus_rdtxt_aes()
        await producer_rdtxt
        dut._log.info("Read Text AES pass")

    async def rdtxt_sha():
        dut._log.info("Read Text SHA start")
        # read text randomized data 32 Bytes
        rd_txt = [randomized_data() for _ in range(RD_TEXT_SHA_BYTES)]
        # read text opcode with randomized opcode, and address 0x654321 
        rd_txtarr = [rd_text_sha_256b(), 0x21, 0x43, 0x65]

        dut.in_bus_valid.value = 1
        for b in rd_txtarr:
            dut.in_bus_data.value = b
            await RisingEdge(dut.clk)

        # deassert bus valid
        dut.in_bus_valid.value = 0
        dut.in_bus_ready.value = 0
        await RisingEdge(dut.clk)


        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1

        # check rd text data matching with randomized back pressure
        async def fsm_cu_rdtxt_sha():
            # read flow fsm -> cu backpressure
            i = 0
            await RisingEdge(dut.clk)
            while i < len(rd_txt):
                dut.in_fsm_data.value = rd_txt[i]
                dut.in_fsm_valid.value = random.randint(0, 1)

                await RisingEdge(dut.clk)
                if dut.in_fsm_valid.value == 1 and int(dut.out_to_fsm_ready.value) == 1:
                    i += 1

            dut.in_fsm_valid.value = 0

        async def cu_bus_rdtxt_sha():
            # read flow cu -> bus
            j = 0
            await RisingEdge(dut.clk)
            while j < len(rd_txt):
                dut.in_bus_ready.value = random.randint(0, 1)
                await RisingEdge(dut.clk)
                if int(dut.out_bus_valid.value) == 1 and dut.in_bus_ready.value == 1:
                    got = int(dut.out_bus_data.value)
                    exp = rd_txt[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

            dut.in_bus_ready.value = 1

        producer_rdtxt = cocotb.start_soon(fsm_cu_rdtxt_sha())
        await cu_bus_rdtxt_sha()
        await producer_rdtxt
        dut._log.info("Read Text SHA pass")


    # read text aes flow 
    await rdtxt_aes()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid

    await rst(dut)  
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.bus_valid.value = 1
    # read text sha flow 
    await rdtxt_sha()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid

    await rst(dut)  
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.bus_valid.value = 1
    # read key flow     
    await rdkey()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid

    dut._log.info("Read Flow comeplete")

async def do_test_write_to_bus(dut):
    # write flow test with backpressure from fsm/bus
    await rst(dut)
    dut._log.info("Write Flow start")   
    await ClockCycles(dut.clk,5)

    # sha write
    async def wrsha():
        # 32 B/256b randomized data
        wr_sha_data = [randomized_data() for _ in range(WR_SHA_BYTES)]

        # write from sha randomized opcode, and address 0xfedcba from 23:0
        wr_sha_dataarr = [wr_sha_generate_256b(), 0xBA, 0xDC, 0xFE]

        dut.in_bus_valid.value = 1
        for b in wr_sha_dataarr:
            dut.in_bus_data.value = b
            await RisingEdge(dut.clk)

        # pull down valid on bus until rising edge of ena
        dut.in_bus_valid.value = 0
        await RisingEdge(dut.clk)
        # bus to cu
        async def bus_cu_wrsha():
            i = 0
            await RisingEdge(dut.clk)
            while i < len(wr_sha_data):
                # bus to cu randomized back pressure
                dut.in_bus_data.value = wr_sha_data[i]
                dut.in_bus_valid.value = random.randint(0, 1)

                await RisingEdge(dut.clk)
                if dut.in_bus_valid.value == 1 and int(dut.out_bus_ready.value) == 1:
                    i += 1

            dut.in_bus_valid.value = 0

        # cu to fsm
        async def cu_fsm_wrsha():
            j = 0
            await RisingEdge(dut.clk)
            while j < len(wr_sha_data):
                # fsm ready randomized back pressure
                dut.in_fsm_ready.value = random.randint(0, 1)
                await RisingEdge(dut.clk)

                if dut.in_fsm_ready.value == 1 and int(dut.out_to_fsm_valid.value) == 1:
                    exp = wr_sha_data[j]
                    got = int(dut.out_fsm_data.value)  # cu -> fsm data
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

            dut.in_fsm_ready.value = 1

        producer_wrsha = cocotb.start_soon(bus_cu_wrsha())
        await cu_fsm_wrsha()
        await producer_wrsha

        dut._log.info("Write SHA pass")


    # aes write
    async def wraes():
        # 16 B/128b randomized data
        wr_aes_data = [randomized_data() for _ in range(WR_AES_BYTES)]

        # write AES opcode + address 0xfedcba from 23:0
        wr_aes_dataarr = [wr_aes_generate_128b(), 0xBA, 0xDC, 0xFE]

        dut.in_bus_valid.value = 1
        for b in wr_aes_dataarr:
            dut.in_bus_data.value = b
            await RisingEdge(dut.clk)

        # pull down valid on bus until rising edge of ena
        dut.in_bus_valid.value = 0
        await RisingEdge(dut.clk)

        # bus to cu
        async def bus_cu_wraes():
            i = 0
            await RisingEdge(dut.clk)
            while i < len(wr_aes_data):
                # bus to cu randomized back pressure
                dut.in_bus_data.value = wr_aes_data[i]
                dut.in_bus_valid.value = random.randint(0, 1)

                await RisingEdge(dut.clk)
                if dut.in_bus_valid.value == 1 and int(dut.out_bus_ready.value) == 1:
                    i += 1

            dut.in_bus_valid.value = 0

        # cu to fsm
        async def cu_fsm_wraes():
            j = 0
            await RisingEdge(dut.clk)
            while j < len(wr_aes_data):
                # fsm ready randomized back pressure
                dut.in_fsm_ready.value = random.randint(0, 1)
                await RisingEdge(dut.clk)

                if dut.in_fsm_ready.value == 1 and int(dut.out_to_fsm_valid.value) == 1:
                    exp = wr_aes_data[j]
                    got = int(dut.out_fsm_data.value)  # cu -> fsm data
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

            dut.in_fsm_ready.value = 1

        producer_wraes = cocotb.start_soon(bus_cu_wraes())
        await cu_fsm_wraes()
        await producer_wraes

        dut._log.info("Write AES pass")

    
    # aes write flow
    await wraes()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid
 
    # sha write flow
    await wrsha()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid 

    dut._log.info("Write Flow complete")      

async def do_test_fsm_handshake(dut):
    # ACK bus test when in_fsm_done == 1, check acknowledgment behavior read/write cases.
    await rst(dut)
    dut._log.info("Ack Flow start")   
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.bus_valid.value = 1
    # read key ack flow test
  
    async def rd_key_ack_flow():
        dut._log.info("Read Key ACK start")
        # data generate
        data = [randomized_data() for _ in range (RD_KEY_AES_BYTES)]
    # read key opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [rd_key_aes_256b(),0xBA, 0xDC, 0xFE]
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)

        # deassert bus calid
        dut.bus_valid.value = 0
        # pull down ready on bus until rise edge of ena     
        await RisingEdge(dut.clk)
        dut.bus_ready.value = 0
        
        # data transfer no backpressure
        dut.bus_ready.value = 1
        dut.fsm_valid.value = 1
        await RisingEdge(dut.clk)
        # 32 Byte
        for i in data:
            dut.in_fsm_bus_data.value = i
            await RisingEdge(dut.clk)
        dut.fsm_valid.value = 0

        # ack asserting 
        # wait for ack request
        await RisingEdge(dut.ack_bus_request)
        # id check
        assert int(dut.ack_bus_id.value) == 0b00, f"ack_bus_id expected{0b00} got {int(dut.ack_bus_id.value):#04b}"
        # arbiter acked
        dut.ack_bus_owned.value = 1
        # pull down bus request
        while dut.ack_bus_request.value == 1:
            await RisingEdge(dut.clk)
        # ack done
        dut.ack_bus_owned.value = 0

        dut._log.info("Read Key Ack complete")
        
    async def rd_txt_ack_flow():
        dut._log.info("Read Text ACK start")
        async def rd_txt_ack_aes():
            dut._log.info("Read Text ACK AES start")
            # data generate
            data = [randomized_data() for _ in range (RD_TEXT_AES_BYTES)]
            # read text opcode with randomized opcode, and address 0xfedcba from 23:0
            opcode = [rd_text_aes_128b(),0xBA, 0xDC, 0xFE]
            for i in opcode:
                dut.in_bus_data.value = i
                await RisingEdge(dut.clk)

            # deassert bus calid
            dut.bus_valid.value = 0
            # pull down ready on bus until rise edge of ena     
            await RisingEdge(dut.clk)
            dut.bus_ready.value = 0
            
            # data transfer no backpressure
            dut.bus_ready.value = 1
            dut.fsm_valid.value = 1
            await RisingEdge(dut.clk)
            # 16 Byte
            for i in data:
                dut.in_fsm_bus_data.value = i
                await RisingEdge(dut.clk)
            dut.fsm_valid.value = 0

            # ack asserting 
            # wait for ack request
            await RisingEdge(dut.ack_bus_request)
            # id check
            assert int(dut.ack_bus_id.value) == 0b00, f"ack_bus_id expected{0b00} got {int(dut.ack_bus_id.value):#04b}"
            # arbiter acked
            dut.ack_bus_owned.value = 1
            # pull down bus request
            while dut.ack_bus_request.value == 1:
                await RisingEdge(dut.clk)
            # ack done
            dut.ack_bus_owned.value = 0
            dut._log.info("Read Text ACK AES pass")

        async def rd_txt_ack_sha():
            dut._log.info("Read Text ACK SHA start")
            # data generate 32 Bytes
            data = [randomized_data() for _ in range (RD_TEXT_SHA_BYTES)]
            # read text opcode with randomized opcode, and address 0xfedcba from 23:0
            opcode = [rd_text_sha_256b(),0xBA, 0xDC, 0xFE]
            for i in opcode:
                dut.in_bus_data.value = i
                await RisingEdge(dut.clk)

            # deassert bus calid
            dut.bus_valid.value = 0
            # pull down ready on bus until rise edge of ena     
            await RisingEdge(dut.clk)
            dut.bus_ready.value = 0
            
            # data transfer no backpressure
            dut.bus_ready.value = 1
            dut.fsm_valid.value = 1
            await RisingEdge(dut.clk)
            # 32 Byte
            for i in data:
                dut.in_fsm_bus_data.value = i
                await RisingEdge(dut.clk)
            dut.fsm_valid.value = 0

            # ack asserting 
            # wait for ack request
            await RisingEdge(dut.ack_bus_request)
            # id check
            assert int(dut.ack_bus_id.value) == 0b00, f"ack_bus_id expected{0b00} got {int(dut.ack_bus_id.value):#04b}"
            # arbiter acked
            dut.ack_bus_owned.value = 1
            # pull down bus request
            while dut.ack_bus_request.value == 1:
                await RisingEdge(dut.clk)
            # ack done
            dut.ack_bus_owned.value = 0
            dut._log.info("Read Text ACK SHA pass")    
        
        await rd_txt_ack_sha()
        await rd_txt_ack_aes()
        dut._log.info("Read Text Ack complete")        

    async def wrsha_ack_flow():
        dut._log.info("Write SHA ACK start")
        # data generate
        data = [randomized_data() for _ in range (WR_SHA_BYTES)]
    # write sha key opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [wr_sha_generate_256b(),0xBA, 0xDC, 0xFE]
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)

        # deassert bus calid
        dut.bus_valid.value = 0
        # pull down ready on bus until rise edge of ena     
        await RisingEdge(dut.clk)
        dut.bus_ready.value = 0
        
        # data transfer no backpressure
        dut.fsm_ready.value = 1
        dut.bus_valid.value = 1
        await RisingEdge(dut.clk)
        # 32 Byte
        for i in data:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        dut.bus_valid.value = 0

        # ack asserting 
        # wait for ack request
        await RisingEdge(dut.ack_bus_request)
        # id check
        assert int(dut.ack_bus_id.value) == 0b00, f"ack_bus_id expected{0b00} got {int(dut.ack_bus_id.value):#04b}"
        # arbiter acked
        dut.ack_bus_owned.value = 1
        # pull down bus request
        while dut.ack_bus_request.value == 1:
            await RisingEdge(dut.clk)
        # ack done
        dut.ack_bus_owned.value = 0

        dut._log.info("Write SHA Ack complete")
        
    async def wraes_ack_flow():
        dut._log.info("Write AES ACK start")
        # data generate
        data = [randomized_data() for _ in range (WR_AES_BYTES)]
    # read text opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [wr_aes_generate_128b(),0xBA, 0xDC, 0xFE]
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)

        # deassert bus calid
        dut.bus_valid.value = 0
        # pull down ready on bus until rise edge of ena     
        await RisingEdge(dut.clk)
        dut.bus_ready.value = 0
        
        # data transfer no backpressure
        dut.bus_valid.value = 1
        dut.fsm_ready.value = 1
        await RisingEdge(dut.clk)
        # 16 Byte
        for i in data:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        dut.bus_valid.value = 0

        # ack asserting 
        # wait for ack request
        await RisingEdge(dut.ack_bus_request)
        # id check
        assert int(dut.ack_bus_id.value) == 0b00, f"ack_bus_id expected{0b00} got {int(dut.ack_bus_id.value):#04b}"
        # arbiter acked
        dut.ack_bus_owned.value = 1
        # pull down bus request
        while dut.ack_bus_request.value == 1:
            await RisingEdge(dut.clk)
        # ack done
        dut.ack_bus_owned.value = 0
        
        dut._log.info("Write AES Ack complete")        

        dut._log.info("Signal Checked")

    await rd_key_ack_flow()

    await rd_txt_ack_flow()

    await wrsha_ack_flow()

    await wraes_ack_flow()


    dut._log.info("ACK flow complete")
