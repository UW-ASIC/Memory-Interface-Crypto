Command Port:

    Connected to bus via bus_port[7:0]

    Constantly poll for bus_port[1:0] for op code, bus_port[5:4] and bus_port[5:4] for MEM as source/dest ID

        Decode these 3 operation: 
            RD_KEY, RD_TEXT, WR_RES

        Then get all of 24 bits of address[24:0] over next 3 beats
            Set address_ready flag and start transaction FSM

        If RD_KEY or RD_TEXT:
            poll FSM data ready, whenever data is ready present data on the bus 8 bits at a time and assert valid for 1 cycle.

        Else If WR_RES: 
            WRITE RES over N(tbd) bytes to the FSM whenever Transaction FSM is ready to receive

        Poll FSM complete, if complete, request for ACK signal.


Transcation FSM:

    Receives data[7:0] from Command Port and activated by start signal

    If opcode == RD_KEY or RD_TEXT:
        Prepare corresponding SPI read command, send to SPI controller whenver ready and start controller

        check if status poller ready, if ready send next bit otherwise spin
  
        poll SPI data ready, whenever ready set data ready for command port until acknowledged

        whenever all SPI transfer finishes. signal FSM complete to the command port

    Else If opcode == WR_RES
        Prepare corresponding SPI write command, send to SPI controller whenver ready and start controller

        check if status poller ready, if ready send next bit otherwise spin
  
        whenever all SPI transfer finishes. signal FSM complete to the command port

    Increment transcations completed every time it's time to send a new one

SPI Controller

    Started by transaction FSM, presented data[7:0] to write, assert SCLK, shift data out of MOSI port

    No matter if there is/isn't data on the MISO bit, always shift it in and set MISO valid bit to 1 when 8 bits are received


Status poller:

    always check if transaction completed is less than total transactions and set/unset valid based on if transactioin is completed



