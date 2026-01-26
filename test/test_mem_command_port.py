# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Clarification required on: 

# data bus control timing

    # input wire clk,
    # input wire rst_n,

    # // --- Bus ---
    # input wire in_bus_valid,
    # input wire in_bus_ready,
    # input wire [7:0] in_bus_data,

    # output reg [7:0] out_bus_data,
    # output wire out_bus_ready,
    # output reg out_bus_valid,
    
    # // --- Ack Bus ---
    # input wire in_ack_bus_owned,
    # output reg out_ack_bus_request,
    # output reg [1:0] out_ack_bus_id,

    # // --- Transaction FSM ---
    # output reg out_fsm_valid,
    # output wire out_fsm_ready,
    # output reg [7:0] out_fsm_data,

    # input wire in_fsm_ready,
    # input wire in_fsm_valid,
    # input wire [7:0] in_fsm_data,
    # input wire in_fsm_done,
    
    # output reg out_fsm_enc_type,
    # output reg [1:0] out_fsm_opcode,
    # output reg [23:0] out_address

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
)
from cocotb.result import SimTimeoutError
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

@cocotb.test(timeout_time= 100,timeout_unit='us')
async def mem_cu(dut):

    dut._log.info("CMD Submodule Start")
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await rst(dut)
    await do_test_valid_header(dut)
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
    # output reg out_fsm_valid,
    # output wire out_fsm_ready,
    # output reg [7:0] out_fsm_data,

    # input wire in_fsm_ready,
    # input wire in_fsm_valid,
    # input wire [7:0] in_fsm_data,
    # input wire in_fsm_done,
    
    # output reg out_fsm_enc_type,
    # output reg [1:0] out_fsm_opcode,
    # output reg [23:0] out_address,

    assert dut.out_fsm_valid.value == 0,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert dut.out_fsm_ready.value == 0,f"out_fsm_ready expecpted 0 got {dut.out_fsm_ready.value}"

    assert int(dut.out_address.value) == 0,f"out_address expecpted 0x000000 got {int(dut.out_address.value):#06x}" 
    assert int(dut.out_fsm_opcode.value) == 0,f"out_fsm_opcode expecpted 0b00 got {int(dut.out_fsm_opcode.value):#02b}" 

    # // --- Bus ---
    # input wire in_bus_valid,
    # input wire in_bus_ready,
    # input wire [7:0] in_bus_data,

    # output reg [7:0] out_bus_data,
    # output wire out_bus_ready,
    # output reg out_bus_valid,

    assert int(dut.out_bus_data.value) == 0,f"out_bus_data expecpted 0x0 got {int(dut.out_bus_data.value):#02x}"
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

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)         
    assert dut.out_fsm_valid.value == 1,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert int(dut.out_address.value) == 0x654321,f"out_address expecpted 0x654321 got {int(dut.out_address.value):#06x}"
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

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)          
    assert dut.out_fsm_valid.value == 1,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert int(dut.out_address.value) == 0x563412,f"out_address expecpted 0x563412 got {int(dut.out_address.value):#06x}"
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

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)  
    assert dut.out_fsm_valid.value == 1,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert int(dut.out_address.value) == 0xfedcba,f"out_address expecpted 0xfedcba got {int(dut.out_address.value):#06x}"
    dut.in_bus_valid.value = 0
    dut.in_fsm_ready.value = 0
    dut.in_fsm_ready.value = 1
    # wait cu to process
    await RisingEdge(dut.clk)

    await rst(dut)
    await ClockCycles(dut.clk,5)
    # valid header addr from 0x654321
    header = [wr_aes_generate_128b(),0x21,0x43,0x65]
    dut.in_bus_valid.value = 1
    dut.in_fsm_ready.value = 1
    for i,b in enumerate(header):
        dut.in_bus_data.value = b
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)          
    await RisingEdge(dut.clk)
    assert dut.out_fsm_valid.value == 1,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert int(dut.out_address.value) == 0x654321,f"out_address expecpted 0x654321 got {int(dut.out_address.value):#06x}"   
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
        
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert dut.out_fsm_valid.value == 1,f"out_fsm_valid expecpted 1 got {dut.out_fsm_valid.value}"
    assert int(dut.out_address.value) == 0x654321,f"out_address expecpted 0x654321 got {int(dut.out_address.value):#06x}"   
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
    dut.in_bus_valid.value = 1 

    for _ in range(10):
        #invalid opcode, and address 0xfedcba from 23:0
    # invalid opcode: check ena signal, valid signal

        # invalid header addr from 0x654321
        header = [invalid() for _ in range (22)]
        dut.in_bus_valid.value = 1
        dut.in_fsm_ready.value = 1
        for i,b in enumerate(header):
            dut.in_bus_data.value = b
            await RisingEdge(dut.clk)

        assert dut.out_fsm_valid.value == 0,f"out_fsm_valid expecpted 0 got {dut.out_fsm_valid.value}"
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
    
    # read key back pressure
    async def rdkey():
        dut._log.info("Read Key AES start")
        # read key randomized data 32 Bytes
        rd_key = [randomized_data() for _ in range(RD_KEY_AES_BYTES)]
        # read key opcode with randomized opcode, and address 0x654321 
        rd_keyarr = [rd_key_aes_256b(),0x21, 0x43, 0x65]

        async def header(byte):
            dut.in_bus_valid.value = 1
            for i in byte:
                dut.in_bus_data.value = i
                # wait until DUT accepts this byte
                while True:
                    await RisingEdge(dut.clk)
                    if int(dut.out_bus_ready.value) == 1:
                        break
            dut.in_bus_valid.value = 0

        await header(rd_keyarr)
        
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1
        # check rd key data matching with randomized back pressure
        async def fsm_cu_rdkey_aes():
            i = 0
            dut.in_fsm_valid.value = 0
            await RisingEdge(dut.clk)

            while i < len(rd_key):
                # random pressure offering next beat
                if pyrandom.randint(0, 1) == 0:
                    dut.in_fsm_valid.value = 0
                    await RisingEdge(dut.clk)
                    continue

                # offer beat i
                dut.in_fsm_data.value  = rd_key[i]
                dut.in_fsm_valid.value = 1

                # hold until CU takes it
                timeout = 2000
                while timeout > 0:
                    await RisingEdge(dut.clk)
                    if int(dut.out_fsm_ready.value) == 1:
                        break
                    timeout -= 1
                assert timeout > 0, "out_fsm_ready never went high (DUT not in read state)"

                i += 1

            dut.in_fsm_valid.value = 0

        async def cu_bus_rdkey_aes():
            # read flow from cu to bus
            j = 0
            await RisingEdge(dut.clk)

            timeout = 5000
            while j < len(rd_key):
                # choose ready 
                dut.in_bus_ready.value = int(pyrandom.randint(0, 1))

                # sample stable signals THIS cycle
                await ReadOnly()

                fire = int(dut.out_bus_valid.value) and int(dut.in_bus_ready.value)
                if fire:
                    got = int(dut.out_bus_data.value)
                    exp = rd_key[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

                await RisingEdge(dut.clk)
                timeout -= 1
                assert timeout > 0, "timeout waiting for bus outputs"

            dut.in_bus_ready.value = 1
            
        producer_rdtxt = cocotb.start_soon(fsm_cu_rdkey_aes())
        await cu_bus_rdkey_aes()
        await producer_rdtxt
        dut._log.info("Read Key AES pass")

    async def rdtxt_aes():
        dut._log.info("Read Text AES start")
        # read text randomized data 16 Bytes
        rd_txt = [randomized_data() for _ in range(RD_TEXT_AES_BYTES)]
        # read text opcode with randomized opcode, and address 0x654321 
        rd_txtarr = [rd_text_aes_128b(),0x21, 0x43, 0x65]

        async def header(byte):
            dut.in_bus_valid.value = 1
            for i in byte:
                dut.in_bus_data.value = i
                # wait until DUT accepts this byte
                while True:
                    await RisingEdge(dut.clk)
                    if int(dut.out_bus_ready.value) == 1:
                        break
            dut.in_bus_valid.value = 0

        await header(rd_txtarr)
        
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1
        # check rd text data matching with randomized back pressure
        async def fsm_cu_rdtxt_aes():
            i = 0
            dut.in_fsm_valid.value = 0
            await RisingEdge(dut.clk)

            while i < len(rd_txt):
                # random pressure offering next beat
                if pyrandom.randint(0, 1) == 0:
                    dut.in_fsm_valid.value = 0
                    await RisingEdge(dut.clk)
                    continue

                # offer beat i
                dut.in_fsm_data.value  = rd_txt[i]
                dut.in_fsm_valid.value = 1

                # hold until CU takes it
                timeout = 2000
                while timeout > 0:
                    await RisingEdge(dut.clk)
                    if int(dut.out_fsm_ready.value) == 1:
                        break
                    timeout -= 1
                assert timeout > 0, "out_fsm_ready never went high (DUT not in read state)"

                i += 1

            dut.in_fsm_valid.value = 0

        async def cu_bus_rdtxt_aes():
            # read flow from cu to bus
            j = 0
            await RisingEdge(dut.clk)

            timeout = 5000
            while j < len(rd_txt):
                # choose ready 
                dut.in_bus_ready.value = int(pyrandom.randint(0, 1))

                # sample stable signals THIS cycle
                await ReadOnly()

                fire = int(dut.out_bus_valid.value) and int(dut.in_bus_ready.value)
                if fire:
                    got = int(dut.out_bus_data.value)
                    exp = rd_txt[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

                await RisingEdge(dut.clk)
                timeout -= 1
                assert timeout > 0, "timeout waiting for bus outputs"

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
        rd_txtarr = [rd_text_sha_256b(),0x21, 0x43, 0x65]

        async def header(byte):
            dut.in_bus_valid.value = 1
            for i in byte:
                dut.in_bus_data.value = i
                # wait until DUT accepts this byte
                while True:
                    await RisingEdge(dut.clk)
                    if int(dut.out_bus_ready.value) == 1:
                        break
            dut.in_bus_valid.value = 0

        await header(rd_txtarr)
        
        await RisingEdge(dut.clk)
        dut.in_bus_ready.value = 1
        # check rd text data matching with randomized back pressure
        async def fsm_cu_rdtxt_sha():
            i = 0
            dut.in_fsm_valid.value = 0
            await RisingEdge(dut.clk)

            while i < len(rd_txt):
                # random pressure offering next beat
                if pyrandom.randint(0, 1) == 0:
                    dut.in_fsm_valid.value = 0
                    await RisingEdge(dut.clk)
                    continue

                # offer beat i
                dut.in_fsm_data.value  = rd_txt[i]
                dut.in_fsm_valid.value = 1

                # hold until CU takes it
                timeout = 2000
                while timeout > 0:
                    await RisingEdge(dut.clk)
                    if int(dut.out_fsm_ready.value) == 1:
                        break
                    timeout -= 1
                assert timeout > 0, "out_fsm_ready never went high (DUT not in read state)"

                i += 1

            dut.in_fsm_valid.value = 0

        async def cu_bus_rdtxt_sha():
            # read flow from cu to bus
            j = 0
            await RisingEdge(dut.clk)

            timeout = 5000
            while j < len(rd_txt):
                # choose ready 
                dut.in_bus_ready.value = int(pyrandom.randint(0, 1))

                # sample stable signals THIS cycle
                await ReadOnly()

                fire = int(dut.out_bus_valid.value) and int(dut.in_bus_ready.value)
                if fire:
                    got = int(dut.out_bus_data.value)
                    exp = rd_txt[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

                await RisingEdge(dut.clk)
                timeout -= 1
                assert timeout > 0, "timeout waiting for bus outputs"

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
    dut.in_bus_valid.value = 1
    # read text sha flow 
    await rdtxt_sha()
    await ClockCycles(dut.clk,5)
    # deassert ena / valid

    await rst(dut)  
    await ClockCycles(dut.clk,5)
    # data bus always valid
    dut.in_bus_valid.value = 1
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

        async def send_bus_bytes(byte):
            dut.in_bus_valid.value = 1
            for b in byte:
                dut.in_bus_data.value = b
                while True:
                    await RisingEdge(dut.clk)
                    if int(dut.out_bus_ready.value):
                        break
            dut.in_bus_valid.value = 0

        await send_bus_bytes(wr_sha_dataarr)
        # bus to cu
        async def bus_cu_wrsha():
            i = 0
            dut.in_bus_valid.value = 0
            await RisingEdge(dut.clk)

            while i < len(wr_sha_data):

                # random bubble BEFORE offering next beat
                if pyrandom.randint(0,1) == 0:
                    dut.in_bus_valid.value = 0
                    await RisingEdge(dut.clk)
                    continue

                # offer beat i
                dut.in_bus_data.value  = wr_sha_data[i]
                dut.in_bus_valid.value = 1

                # hold until CU accepts (fire)
                timeout = 2000
                while timeout > 0:
                    await ReadOnly()  # check ready for this cycle
                    if int(dut.out_bus_ready.value):
                        # fire will complete at the upcoming edge
                        await RisingEdge(dut.clk)
                        break
                    # not ready this cycle, keep holding
                    await RisingEdge(dut.clk)
                    timeout -= 1

                assert timeout > 0, "timeout waiting for out_bus_ready"
                i += 1

            dut.in_bus_valid.value = 0

        # cu to fsm
        async def cu_fsm_wrsha():
            j = 0
            await RisingEdge(dut.clk)

            timeout = 5000
            while j < len(wr_sha_data):
                dut.in_fsm_ready.value = int(pyrandom.randint(0, 1))

                await ReadOnly()  # sample stable THIS cycle

                if int(dut.out_fsm_valid.value) and int(dut.in_fsm_ready.value):
                    got = int(dut.out_fsm_data.value)
                    exp = wr_sha_data[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

                await RisingEdge(dut.clk)
                timeout -= 1
                assert timeout > 0, "timeout waiting for cu - fsm"

            dut.in_fsm_ready.value = 1
        await RisingEdge(dut.clk)
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

        async def send_bus_bytes(byte):
            dut.in_bus_valid.value = 1
            for b in byte:
                dut.in_bus_data.value = b
                while True:
                    await RisingEdge(dut.clk)
                    if int(dut.out_bus_ready.value):
                        break
            dut.in_bus_valid.value = 0

        await send_bus_bytes(wr_aes_dataarr)

        # bus to cu
        async def bus_cu_wraes():
            i = 0
            dut.in_bus_valid.value = 0
            await RisingEdge(dut.clk)

            while i < len(wr_aes_data):

                # random bubble BEFORE offering next beat
                if pyrandom.randint(0,1) == 0:
                    dut.in_bus_valid.value = 0
                    await RisingEdge(dut.clk)
                    continue

                # offer beat i
                dut.in_bus_data.value  = wr_aes_data[i]
                dut.in_bus_valid.value = 1

                # hold until CU accepts (fire)
                timeout = 2000
                while timeout > 0:
                    await ReadOnly()  # check ready for THIS cycle
                    if int(dut.out_bus_ready.value):
                        # fire will complete at the upcoming edge
                        await RisingEdge(dut.clk)
                        break
                    # not ready this cycle, keep holding
                    await RisingEdge(dut.clk)
                    timeout -= 1

                assert timeout > 0, "timeout waiting for out_bus_ready"
                i += 1

            dut.in_bus_valid.value = 0

        # cu to fsm

        async def cu_fsm_wraes():
            j = 0
            await RisingEdge(dut.clk)

            timeout = 5000
            while j < len(wr_aes_data):
                dut.in_fsm_ready.value = int(pyrandom.randint(0, 1))

                await ReadOnly()  # sample stable THIS cycle

                if int(dut.out_fsm_valid.value) and int(dut.in_fsm_ready.value):
                    got = int(dut.out_fsm_data.value)
                    exp = wr_aes_data[j]
                    assert got == exp, f"[byte {j}] expected {exp:#04x}, got {got:#04x}"
                    j += 1

                await RisingEdge(dut.clk)
                timeout -= 1
                assert timeout > 0, "timeout waiting for cu - fsm"

            dut.in_fsm_ready.value = 1
        await RisingEdge(dut.clk)
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
    dut.in_bus_valid.value = 1
    # read key ack flow test
  
    async def rd_key_ack_flow():
        dut._log.info("Read Key ACK start")
        # data generate
        data = [randomized_data() for _ in range (RD_KEY_AES_BYTES)]
        # read key opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [rd_key_aes_256b(),0xBA, 0xDC, 0xFE]
        dut.in_bus_valid.value = 1
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        
        # data transfer no backpressure
        dut.in_bus_ready.value = 1
        dut.in_fsm_valid.value = 1
        await RisingEdge(dut.clk)
        # 32 Byte
        for i in data:
            dut.in_fsm_data.value = i
            await RisingEdge(dut.clk)

        dut.in_fsm_valid.value = 0
        dut.in_bus_valid.value = 0
        # done signal
        dut.in_fsm_done.value = 1
        # ack asserting 
        # wait for ack request
        await RisingEdge(dut.out_ack_bus_request)
        # id check
        assert int(dut.out_ack_bus_id.value) == 0b00, f"out_ack_bus_id expected{0b00} got {int(dut.out_ack_bus_id.value):#04b}"
        # arbiter acked
        dut.in_ack_bus_owned.value = 1
        # pull down bus request
        while dut.out_ack_bus_request.value == 1:
            await RisingEdge(dut.clk)
        # ack done
        dut.in_ack_bus_owned.value = 0
        dut.in_fsm_done.value = 0
        dut._log.info("Read Key Ack complete")
        
    async def rd_txt_ack_flow():
        dut._log.info("Read Text ACK start")
        async def rd_txt_ack_aes():
            dut._log.info("Read Text ACK AES start")
            # data generate
            data = [randomized_data() for _ in range (RD_TEXT_AES_BYTES)]
            # read text opcode with randomized opcode, and address 0xfedcba from 23:0
            opcode = [rd_text_aes_128b(),0xBA, 0xDC, 0xFE]

            dut.in_bus_valid.value = 1

            for i in opcode:
                dut.in_bus_data.value = i
                await RisingEdge(dut.clk)
            
            # data transfer no backpressure
            dut.in_bus_ready.value = 1
            dut.in_fsm_valid.value = 1
            await RisingEdge(dut.clk)
            # 16 Byte
            for i in data:
                dut.in_fsm_data.value = i
                await RisingEdge(dut.clk)
            dut.in_fsm_valid.value = 0
            dut.in_bus_valid.value = 0
            # done signal
            dut.in_fsm_done.value = 1
            # ack asserting 
            # wait for ack request
            await RisingEdge(dut.out_ack_bus_request)
            # id check
            assert int(dut.out_ack_bus_id.value) == 0b00, f"out_ack_bus_id expected{0b00} got {int(dut.out_ack_bus_id.value):#04b}"
            # arbiter acked
            dut.in_ack_bus_owned.value = 1
            # pull down bus request
            while dut.out_ack_bus_request.value == 1:
                await RisingEdge(dut.clk)
            # ack done
            dut.in_ack_bus_owned.value = 0
            dut.in_fsm_done.value = 0
            dut._log.info("Read Text ACK AES pass")

        async def rd_txt_ack_sha():
            dut._log.info("Read Text ACK SHA start")
            # data generate 32 Bytes
            data = [randomized_data() for _ in range (RD_TEXT_SHA_BYTES)]
            # read text opcode with randomized opcode, and address 0xfedcba from 23:0
            opcode = [rd_text_sha_256b(),0xBA, 0xDC, 0xFE]
            
            dut.in_bus_valid.value = 1
            for i in opcode:
                dut.in_bus_data.value = i
                await RisingEdge(dut.clk)
           
            # data transfer no backpressure
            dut.in_bus_ready.value = 1
            dut.in_fsm_valid.value = 1
            await RisingEdge(dut.clk)
            # 32 Byte
            for i in data:
                dut.in_fsm_data.value = i
                await RisingEdge(dut.clk)
            dut.in_fsm_valid.value = 0
            dut.in_bus_valid.value = 0
            # done signal
            dut.in_fsm_done.value = 1
            # ack asserting 
            # wait for ack request
            await RisingEdge(dut.out_ack_bus_request)
            # id check
            assert int(dut.out_ack_bus_id.value) == 0b00, f"out_ack_bus_id expected{0b00} got {int(dut.out_ack_bus_id.value):#04b}"
            # arbiter acked
            dut.in_ack_bus_owned.value = 1
            # pull down bus request
            while dut.out_ack_bus_request.value == 1:
                await RisingEdge(dut.clk)
            # ack done
            dut.in_ack_bus_owned.value = 0
            dut.in_fsm_done.value = 0
            dut._log.info("Read Text ACK SHA pass")    
        
        await rd_txt_ack_sha()
        await ClockCycles(dut.clk,5)
        await rd_txt_ack_aes()
        dut._log.info("Read Text Ack complete")        

    async def wrsha_ack_flow():
        dut._log.info("Write SHA ACK start")
        # data generate
        data = [randomized_data() for _ in range (WR_SHA_BYTES)]
    # write sha key opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [wr_sha_generate_256b(),0xBA, 0xDC, 0xFE]
        dut.in_bus_valid.value = 1
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        
        # data transfer no backpressure
        dut.in_fsm_ready.value = 1
        dut.in_bus_valid.value = 1
        await RisingEdge(dut.clk)
        # 32 Byte
        for i in data:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        dut.in_bus_valid.value = 0
        # done signal
        dut.in_fsm_done.value = 1
        # ack asserting 
        # wait for ack request
        # await RisingEdge(dut.out_ack_bus_request)
        # # id check
        # assert int(dut.out_ack_bus_id.value) == 0b00, f"out_ack_bus_id expected{0b00} got {int(dut.out_ack_bus_id.value):#04b}"
        # # arbiter acked
        # dut.in_ack_bus_owned.value = 1
        # # pull down bus request
        # while dut.out_ack_bus_request.value == 1:
        #     await RisingEdge(dut.clk)
        # # ack done
        # dut.in_ack_bus_owned.value = 0
        await RisingEdge(dut.clk)
        dut.in_fsm_done.value = 0
        for _ in range(10):
            assert dut.out_ack_bus_request.value == 0, f"dut.out_ack_bus_request.value expect 0 got {dut.out_ack_bus_request.value}"
            await RisingEdge(dut.clk)
        # dut.in_fsm_done.value = 0
        dut._log.info("Write SHA Ack complete")
        
    async def wraes_ack_flow():
        dut._log.info("Write AES ACK start")
        # data generate
        data = [randomized_data() for _ in range (WR_AES_BYTES)]
        # read text opcode with randomized opcode, and address 0xfedcba from 23:0
        opcode = [wr_aes_generate_128b(),0xBA, 0xDC, 0xFE]
        dut.in_bus_valid.value = 1
        for i in opcode:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)

        # data transfer no backpressure
        dut.in_bus_valid.value = 1
        dut.in_fsm_ready.value = 1
        await RisingEdge(dut.clk)
        # 16 Byte
        for i in data:
            dut.in_bus_data.value = i
            await RisingEdge(dut.clk)
        dut.in_bus_valid.value = 0
        # done signal
        dut.in_fsm_done.value = 1
        # ack asserting 
        
        # wait for ack request
        # await RisingEdge(dut.out_ack_bus_request)
        # # id check
        # assert int(dut.out_ack_bus_id.value) == 0b00, f"out_ack_bus_id expected{0b00} got {int(dut.out_ack_bus_id.value):#04b}"
        # # arbiter acked
        # dut.in_ack_bus_owned.value = 1
        # # pull down bus request
        # while dut.out_ack_bus_request.value == 1:
        #     await RisingEdge(dut.clk)
        # # ack done
        # dut.in_ack_bus_owned.value = 0
        await RisingEdge(dut.clk)
        dut.in_fsm_done.value = 0
        for _ in range(10):
            assert dut.out_ack_bus_request.value == 0, f"dut.out_ack_bus_request.value expect 0 got {dut.out_ack_bus_request.value}"
            await RisingEdge(dut.clk)
        dut._log.info("Write AES Ack complete")        

    await rd_key_ack_flow()
    # await with_timeout(rd_key_ack_flow(),2000,'ms')
    await rd_txt_ack_flow()
    # await with_timeout(rd_txt_ack_flow(),2000,'ms')
    await wrsha_ack_flow()
    # await with_timeout(wrsha_ack_flow(),2000,'ms')
    await wraes_ack_flow()
    # await with_timeout(wraes_ack_flow(),2000,'ms')

    dut._log.info("ACK flow complete")
