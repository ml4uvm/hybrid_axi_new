import os
import csv

from pyuvm import uvm_env, uvm_agent, uvm_sequencer
from pyuvm.s12_uvm_tlm_interfaces import uvm_analysis_export

from tb.components.driver import AXIDriver
from tb.components.monitor import AXIMonitor
from tb.components.scoreboard import AXIScoreboard


# =========================================================
# Address / data classification
# =========================================================

def classify_addr(addr):
    """
    Address category classification, per the locked 18-bin model.

    The same categories apply to both WRITE and READ addresses --
    REG0-REG3 map 1:1 onto the 4-entry regfile; everything else is
    INVALID (verified against the RTL: every address 4-255 is
    treated identically, no secondary decode).
    """

    if 0 <= addr < 4:
        return f"REG{addr}"

    return "INVALID"


def classify_data(wdata):
    """
    UNSIGNED data classification.

    WDATA has no signed interpretation anywhere in this RTL
    (unlike the ALU's operand classification), so this must NOT
    use a to_signed()-style conversion.
    """

    if wdata == 0:
        return "ZERO"
    elif 0 < wdata < 10:
        return "SMALL"
    else:
        return "LARGE"


# =========================================================
# Coverage bin classification -- SINGLE SOURCE OF TRUTH
# =========================================================

def get_bin(item):
    """
    Coverage bin classification for the locked 18-bin model.

    WRITE:
        REG0-REG3 x {ZERO, SMALL, LARGE}
        = 12 bins

        INVALID WRITE
        = 1 bin

    READ:
        REG0
        REG1
        REG2
        REG3
        INVALID
        = 5 bins

    Total = 18 bins
    """

    addr_cat = classify_addr(item.addr)

    if item.txn_type == "READ":
        return ("READ", addr_cat)

    # WRITE
    if addr_cat == "INVALID":
        return ("WRITE", "INVALID", "NA")

    data_type = classify_data(item.wdata)

    return (
        "WRITE",
        addr_cat,
        data_type,
    )


TOTAL_BINS = 18
covered_bins = set()

# =========================================================
# Hybrid coverage helper APIs
# =========================================================

def get_covered_bins():
    """
    Return all currently covered functional coverage bins.
    """
    return set(covered_bins)


def get_uncovered_bins():
    """
    Return all uncovered functional coverage bins.
    """
    all_bins = set()

    # WRITE bins
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        for dtype in ["ZERO", "SMALL", "LARGE"]:
            all_bins.add(("WRITE", reg, dtype))

    all_bins.add(("WRITE", "INVALID", "NA"))

    # READ bins
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        all_bins.add(("READ", reg))

    all_bins.add(("READ", "INVALID"))

    return all_bins - covered_bins


def coverage_complete():
    """
    Returns True if all functional coverage bins are covered.
    """
    return len(covered_bins) >= TOTAL_BINS

# =========================================================
# COVERAGE + CSV LOGGER
# =========================================================

class CoverageExport(uvm_analysis_export):

    def build_phase(self):
        self.write = self.write

    def start_of_simulation_phase(self):
        os.makedirs("results", exist_ok=True)
        

        self.log_file = open(
            "results/coverage_log.csv",
            "w",
            newline=""
        )

        self.writer = csv.writer(self.log_file)

        self.writer.writerow([
            "txn_type",
            "addr",
            "addr_category",
            "wdata",
            "rdata",
            "data_type",
            "bresp",
            "rresp",
            "cov_gain",
            "gain_label",
        ])

    def write(self, item):
       

        bin_key = get_bin(item)

        old_cov = len(covered_bins)

        covered_bins.add(bin_key)

        new_cov = len(covered_bins)

        coverage_gain = new_cov - old_cov

        gain_label = 1 if coverage_gain > 0 else 0

        # Derive CSV columns directly from the coverage bin
        if item.txn_type == "WRITE":
            _, addr_cat, data_type = bin_key
        else:
            _, addr_cat = bin_key
            data_type = "NA"

                
        self.writer.writerow([
            item.txn_type,
            item.addr,
            addr_cat,
            item.wdata,
            item.rdata,
            data_type,
            item.bresp,
            item.rresp,
            coverage_gain,
            gain_label,
        ])
        self.log_file.flush()
       

    def final_phase(self):
        self.log_file.close()

        print(
            f"Coverage: {len(covered_bins)}/{TOTAL_BINS} bins hit"
        )


# =========================================================
# AGENT
# =========================================================

class AXIAgent(uvm_agent):

    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        self.driver = AXIDriver("driver", self)
        self.monitor = AXIMonitor("monitor", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(
            self.seqr.seq_item_export
        )


# =========================================================
# ENVIRONMENT
# =========================================================

class AXIEnv(uvm_env):

    def build_phase(self):
        self.agent = AXIAgent("agent", self)
        self.cov_export = CoverageExport(
            "cov_export",
            self,
        )
        self.scoreboard = AXIScoreboard(
            "scoreboard",
            self,
        )

    def connect_phase(self):
        # Monitor -> Coverage
        self.agent.monitor.ap.connect(
            self.cov_export
        )

        # Monitor -> Scoreboard
        self.agent.monitor.ap.connect(
            self.scoreboard.analysis_export
        )
