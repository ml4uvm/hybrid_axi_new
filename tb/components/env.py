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
    Address category classification.
    """

    if 0 <= addr < 4:
        return f"REG{addr}"

    return "INVALID"


def classify_data(wdata):
    """
    UNSIGNED data classification.
    """

    if wdata == 0:
        return "ZERO"
    elif 0 < wdata < 10:
        return "SMALL"
    else:
        return "LARGE"


# =========================================================
# Coverage bin classification
# =========================================================

def get_bin(item):

    addr_cat = classify_addr(item.addr)

    if item.txn_type == "READ":
        return ("READ", addr_cat)

    if addr_cat == "INVALID":
        return ("WRITE", "INVALID", "NA")

    data_type = classify_data(item.wdata)

    return (
        "WRITE",
        addr_cat,
        data_type,
    )


# =========================================================
# Coverage state
# =========================================================

TOTAL_BINS = 26

covered_bins = set()

# Stores previous transaction for sequence-based coverage
last_txn = None


# =========================================================
# Hybrid coverage helper APIs
# =========================================================

def get_covered_bins():
    """
    Return all covered bins.
    """
    return set(covered_bins)


def get_uncovered_bins():
    """
    Return all uncovered bins.
    """

    all_bins = set()

    # -------------------------
    # WRITE bins
    # -------------------------
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        for dtype in ["ZERO", "SMALL", "LARGE"]:
            all_bins.add(("WRITE", reg, dtype))

    all_bins.add(("WRITE", "INVALID", "NA"))

    # -------------------------
    # READ bins
    # -------------------------
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        all_bins.add(("READ", reg))

    all_bins.add(("READ", "INVALID"))

    # -------------------------
    # RAW bins
    # -------------------------
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        all_bins.add(("RAW", reg))

    # -------------------------
    # DOUBLE WRITE bins
    # -------------------------
    for reg in ["REG0", "REG1", "REG2", "REG3"]:
        all_bins.add(("DOUBLE_WRITE", reg))

    return all_bins - covered_bins


def coverage_complete():
    """
    Returns True if all coverage bins are covered.
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

        global last_txn

        bin_key = get_bin(item)

        old_cov = len(covered_bins)

        # Original coverage
        covered_bins.add(bin_key)

        # -----------------------------
        # RAW coverage
        # -----------------------------
        if (
            last_txn is not None
            and last_txn.txn_type == "WRITE"
            and item.txn_type == "READ"
        ):

            prev_reg = classify_addr(last_txn.addr)
            curr_reg = classify_addr(item.addr)

            if prev_reg == curr_reg and prev_reg != "INVALID":
                covered_bins.add(("RAW", curr_reg))

        # -----------------------------
        # DOUBLE WRITE coverage
        # -----------------------------
        if (
            last_txn is not None
            and last_txn.txn_type == "WRITE"
            and item.txn_type == "WRITE"
        ):

            prev_reg = classify_addr(last_txn.addr)
            curr_reg = classify_addr(item.addr)

            if prev_reg == curr_reg and prev_reg != "INVALID":
                covered_bins.add(("DOUBLE_WRITE", curr_reg))

        # Save current transaction
        last_txn = item

        new_cov = len(covered_bins)

        coverage_gain = new_cov - old_cov

        gain_label = 1 if coverage_gain > 0 else 0

        # CSV columns
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
