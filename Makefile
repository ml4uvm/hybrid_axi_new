SIM = icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES = $(PWD)/rtl/axi.sv

TOPLEVEL = axi4lite_slave

COCOTB_TEST_MODULES = tb.tests.axi_test

export COCOTB_LOG_LEVEL = WARNING
export COCOTB_RESULTS_FILE = logs/results.xml

$(shell mkdir -p logs)

include $(shell cocotb-config --makefiles)/Makefile.sim