# Memory Interface General Test Plans

---

## command_port

### Overview

Purpose: Facilitate communication between the MEM module and the system bus. Decode incoming commands, acknowledge valid MEM operations, and forward them to the Transaction FSM.

Interfaces:

* System bus (`in_bus`, `out_bus`)
* Transaction FSM command and data handshakes
* Acknowledgement signaling

### Features to Verify

1. Header Decode – Parse opcode, source/dest IDs, and address from `in_bus`.
2. Command Generation – Drive `out_cmd_fsm_valid/opcode/addr` for valid MEM operations.
3. Handshake with FSM – Hold `out_cmd_fsm_valid` until `in_cmd_fsm_ready`.
4. Data Transfer (Read) – When `in_rd_fsm_valid`, output data on `out_bus` for one cycle per byte.
5. Data Transfer (Write) – Send data to FSM via `out_wr_fsm_valid/data` when `in_wr_fsm_ready`.
6. Transaction Completion – Detect `in_fsm_done` and assert acknowledgment.
7. Reset – Deassert all outputs.

### Test Cases

* 1 – Reset Behavior: `rst_n` asserted/deasserted, expect all signals idle.
* 2 – Decode RD_KEY Header: Valid MEM command decoded; check opcode/address.
* 3 – Decode RD_TEXT Header: Same as RD_KEY but opcode=2'b01.
* 4 – Decode WR_RES Header: Opcode=2'b10, verify address and output handshake.
* 5 – Ignore Invalid Header: MEM not destination → no FSM command.
* 6 – Read Data Flow: FSM drives `in_rd_fsm_valid`; Command Port drives `out_bus` for each byte.
* 7 – Write Data Flow: Input data on bus passed to FSM correctly.
* 8 – ACK Assertion: When `in_fsm_done == 1`, check acknowledgment behavior.

---

## transaction_fsm

### Overview

Purpose: Translate MEM commands into SPI flash operations. Sequences the read/write cycles and manages byte transfers with the SPI controller.

### Features to Verify

1. Command Acceptance – Capture `in_cmd_valid/in_cmd_opcode/in_cmd_addr` when ready.
2. SPI Translation – Generate SPI start, length, and correct byte sequences.
3. Data Handshaking – Handle `in_wr_data_valid`/`in_spi_tx_ready` and `in_spi_rx_valid`/`in_wr_cp_ready`.
4. Completion Signaling – End operation and notify command_port.
5. Reset – Clear outputs and internal state.

### Test Cases

* 1 – Reset / Idle: On reset, FSM outputs idle.
* 2 – RD_KEY Command: Translate to SPI read sequence; verify SPI start.
* 3 – RD_TEXT Command: Similar to RD_KEY; verify proper data routing to Command Port.
* 4 – WR_RES Command: Translate to SPI write sequence; verify SPI TX.
* 5 – Data Handshake Robustness: Handle stalls on `in_spi_tx_ready` or `in_wr_cp_ready`.
* 6 – Completion Pulse: Assert done after `in_spi_done`.
* 7 – Reset Mid-Transaction: FSM returns to idle.
* TODO: Confirm if there should be a difference in behavior between read text and read key, and if so how to determine that

---

## spi_controller

### Overview

Purpose: Perform SPI data shifting between Transaction FSM and external flash device, handling all timing and control signals (CS, SCLK, MOSI, MISO).

### Features to Verify

1. Start/Busy/Done Logic – Proper assertion timing.
2. Bit Shifting – MOSI output MSB-first; MISO captured on correct edge.
3. Clock Generation – SCLK toggles consistently during active transfer.
4. Ready/Valid Handshakes – Proper synchronization on TX/RX.
5. Reset Behavior – CS high, SCLK low, busy cleared.

### Test Cases

* 1 – Reset / Idle: Check CS and clock idle states.
* 2 – Single Byte Transfer: Validate MOSI/MISO operation and byte capture.
* 3 – Multi-Byte Transfer: Confirm continuous clocking.
* 4 – Read Backpressure: Hold `in_rx_ready = 0`; verify stall behavior.
* 5 – Write Backpressure: Delay `in_tx_valid`; verify clock gating.
* 6 – Back-to-Back Transfers: Distinct CS periods and done pulses.
* 7 – Continuous Sampling: Confirm correct bit order and timing.

---

## status_poller

### Overview

Purpose: Monitor transaction completion count and signal readiness for next transfer or indicate all-done state.

### Features to Verify

1. Ready Logic – `ready=1` when completed < total.
2. All-Done Logic – `all_done_valid=1` when completed == total.
3. Reset – Outputs clear.

### Test Cases

* 1 – Reset / Idle: Outputs deasserted.
* 2 – Ready Assertion: completed < total → `ready=1`.
* 3 – All Done Assertion: completed == total → `all_done_valid=1`.
* 4 – Deassert Ready: Transition from less-than to equal.
* 5 – Continuous Update: Verify transitions as count increases.
