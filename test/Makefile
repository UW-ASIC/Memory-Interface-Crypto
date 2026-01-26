# Makefile for cocotb tests
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# ============================================================================
# Usage:
#   make test_command_port       - Run command port tests
#   make test_spi_controller     - Run SPI controller tests
#   make test_transaction_fsm    - Run transaction FSM tests
#   make test_mem_top            - Run mem_top tests (needs flash model)
#   make test_tt_toplevel        - Run TinyTapeout toplevel tests
#   make all_tests               - Run all tests
#   make cleanall                - Clean build artifacts
#
# Gate-level simulation:
#   make test_command_port GATES=yes
#   Requires: PDK_ROOT env var, gate_level_netlist.v in test/
# ============================================================================

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src

# Default source files
SRC_FILES ?= mem_command_port.v mem_spi_controller.v mem_txn_fsm.v mem_top.v mem_vendor_test.v W25Q128JVxIM.v

# Testbench file (optional, for tt_toplevel)
TB_FILE ?=

# Include path
COMPILE_ARGS += -I$(SRC_DIR)

# ============================================================================
# Gate Level vs RTL Simulation
# ============================================================================
ifneq ($(GATES),yes)
# RTL simulation
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(SRC_FILES))
ifneq ($(TB_FILE),)
VERILOG_SOURCES += $(PWD)/$(TB_FILE)
endif
COMPILE_ARGS += -DSIMULATION
else


# Gate level simulation
SIM_BUILD = sim_build/gl
COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
ifneq ($(TB_FILE),)
VERILOG_SOURCES += $(PWD)/$(TB_FILE)
endif
endif

# Default toplevel and module (for direct 'make' invocation)
TOPLEVEL ?= mem_vendor_test
MODULE ?= test_mem_top

# ============================================================================
# Test Targets (only at top level, not in recursive calls)
# ============================================================================
.PHONY: test_command_port test_spi_controller test_transaction_fsm test_mem_top test_tt_toplevel all_tests cleanall

ifeq ($(MAKELEVEL),0)

test_command_port:
	rm -rf sim_build
	$(MAKE) -f $(firstword $(MAKEFILE_LIST)) \
		TOPLEVEL=mem_command_port \
		MODULE=test_mem_command_port \
		SRC_FILES="mem_command_port.v"

test_spi_controller:
	rm -rf sim_build
	$(MAKE) -f $(firstword $(MAKEFILE_LIST)) \
		TOPLEVEL=mem_spi_controller \
		MODULE=test_mem_spi_controller \
		SRC_FILES="mem_spi_controller.v"

test_transaction_fsm:
	rm -rf sim_build
	$(MAKE) -f $(firstword $(MAKEFILE_LIST)) \
		TOPLEVEL=mem_txn_fsm \
		MODULE=test_mem_transaction_fsm \
		SRC_FILES="mem_txn_fsm.v"

test_mem_top:
	rm -rf sim_build
	$(MAKE) -f $(firstword $(MAKEFILE_LIST)) \
		TOPLEVEL=mem_vendor_test \
		MODULE=test_mem_top \
		SRC_FILES="mem_command_port.v mem_spi_controller.v mem_txn_fsm.v mem_top.v mem_vendor_test.v W25Q128JVxIM.v"

test_tt_toplevel:
	rm -rf sim_build
	$(MAKE) -f $(firstword $(MAKEFILE_LIST)) \
		TOPLEVEL=tb \
		MODULE=test_tt_um_mem_toplevel \
		SRC_FILES="mem_command_port.v mem_spi_controller.v mem_txn_fsm.v mem_top.v tt_um_mem_toplevel.v" \
		TB_FILE="tb_tt_um_mem_toplevel.v"

all_tests:
	@echo "Running test_command_port..."
	$(MAKE) test_command_port
	@echo "Running test_spi_controller..."
	$(MAKE) test_spi_controller
	@echo "Running test_transaction_fsm..."
	$(MAKE) test_transaction_fsm
	@echo "Running test_mem_top..."
	$(MAKE) test_mem_top
	@echo "All tests completed!"

cleanall:
	rm -rf sim_build __pycache__
	rm -f results.xml *.vcd

endif

# Include cocotb's make rules
include $(shell cocotb-config --makefiles)/Makefile.sim
