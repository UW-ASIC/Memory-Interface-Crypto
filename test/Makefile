# Makefile for cocotb tests
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# ============================================================================
# Usage:
#   make                         - Run default test (RTL: tt_toplevel)
#   make test_command_port       - Run command port tests (RTL only)
#   make test_spi_controller     - Run SPI controller tests (RTL only)
#   make test_transaction_fsm    - Run transaction FSM tests (RTL only)
#   make test_mem_top            - Run mem_top tests (RTL only, needs flash model)
#   make test_tt_toplevel        - Run TinyTapeout toplevel tests (RTL only)
#   make all_tests               - Run all RTL tests
#   make clean                   - Clean build artifacts
#
# Gate-level simulation (tests synthesized top-level only):
#   make GATES=yes
#   Requires: PDK_ROOT env var, gate_level_netlist.v in test/
# ============================================================================

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src

PROJECT_SOURCES = mem_command_port.v \
                  mem_spi_controller.v \
                  mem_txn_fsm.v \
                  mem_top.v \
                  tt_um_mem_toplevel.v

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS += -I$(SRC_DIR)

ifneq ($(GATES),yes)

# ============================================================================
# RTL simulation
# ============================================================================
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
VERILOG_SOURCES += $(PWD)/tb_tt_um_mem_toplevel.v
COMPILE_ARGS += -DSIMULATION

# Default for RTL
TOPLEVEL ?= tb
MODULE ?= test_tt_um_mem_toplevel

.PHONY: test_command_port test_spi_controller test_transaction_fsm test_mem_top test_tt_toplevel all_tests clean cleanall

test_command_port:
	$(MAKE) clean
	$(MAKE) sim \
		MODULE=test_mem_command_port \
		TOPLEVEL=mem_command_port \
		VERILOG_SOURCES="$(SRC_DIR)/mem_command_port.v"

test_spi_controller:
	$(MAKE) clean
	$(MAKE) sim \
		MODULE=test_mem_spi_controller \
		TOPLEVEL=mem_spi_controller \
		VERILOG_SOURCES="$(SRC_DIR)/mem_spi_controller.v"

test_transaction_fsm:
	$(MAKE) clean
	$(MAKE) sim \
		MODULE=test_mem_transaction_fsm \
		TOPLEVEL=mem_txn_fsm \
		VERILOG_SOURCES="$(SRC_DIR)/mem_txn_fsm.v" \
		COMPILE_ARGS="$(COMPILE_ARGS) -DSIMULATION"

test_mem_top:
	$(MAKE) clean
	$(MAKE) sim \
		MODULE=test_mem_top \
		TOPLEVEL=mem_vendor_test \
		VERILOG_SOURCES="$(SRC_DIR)/mem_command_port.v $(SRC_DIR)/mem_spi_controller.v $(SRC_DIR)/mem_txn_fsm.v $(SRC_DIR)/mem_top.v $(SRC_DIR)/mem_vendor_test.v $(SRC_DIR)/W25Q128JVxIM.v"

test_tt_toplevel:
	$(MAKE) clean
	$(MAKE) sim \
		MODULE=test_tt_um_mem_toplevel \
		TOPLEVEL=tb \
		VERILOG_SOURCES="$(SRC_DIR)/mem_command_port.v $(SRC_DIR)/mem_spi_controller.v $(SRC_DIR)/mem_txn_fsm.v $(SRC_DIR)/mem_top.v $(SRC_DIR)/tt_um_mem_toplevel.v $(PWD)/tb_tt_um_mem_toplevel.v"

all_tests: test_command_port test_spi_controller test_transaction_fsm test_mem_top test_tt_toplevel
	@echo "All tests completed!"

else

# ============================================================================
# Gate level simulation (can only test synthesized top-level)
# ============================================================================
SIM_BUILD = sim_build/gl
COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
VERILOG_SOURCES += $(PWD)/tb_tt_um_mem_toplevel.v

# For GL, can only test the synthesized top-level module
TOPLEVEL ?= tb
MODULE ?= test_tt_um_mem_toplevel

.PHONY: clean cleanall

endif

# Phony target for cleaning up
clean::
	rm -rf sim_build results.xml *.vcd __pycache__

cleanall: clean

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
