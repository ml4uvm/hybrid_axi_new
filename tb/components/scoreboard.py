from pyuvm import uvm_component
from pyuvm.s12_uvm_tlm_interfaces import uvm_analysis_export


class AXIScoreboard(uvm_component):
    """
    Independent shadow-model scoreboard for the AXI4-Lite slave.

    Maintains its own 4-entry regfile model, initialized to 0
    (mirroring the RTL's reset behavior), and updates it purely
    from observed WRITE transactions.

    Checks performed:

    WRITE:
        - BRESP matches expected response.
        - Shadow regfile updated only for valid addresses.

    READ:
        - RRESP matches expected response.
        - RDATA matches shadow regfile (or DEADBEEF for invalid).

    The scoreboard intentionally derives expected behavior
    independently of the driver and monitor.
    """

    OKAY = 0b00
    SLVERR = 0b10

    RESET_INVALID_RDATA = 0xDEADBEEF

    def build_phase(self):
        self.analysis_export = uvm_analysis_export(
            "analysis_export",
            self
        )

        self.analysis_export.write = self.write

        # Shadow model of the DUT register file
        self.regfile = [0, 0, 0, 0]

    def write(self, item):
        if item.txn_type == "WRITE":
            self._check_write(item)
        else:
            self._check_read(item)

    # ==========================================================
    # WRITE check
    # ==========================================================

    def _check_write(self, item):

        valid = 0 <= item.addr < 4

        expected_bresp = self.OKAY if valid else self.SLVERR

        assert item.bresp == expected_bresp, (
            f"BRESP mismatch on WRITE: "
            f"addr={item.addr}, "
            f"expected={expected_bresp:#04b}, "
            f"got={item.bresp:#04b}"
        )

        if valid:
            self.regfile[item.addr] = (
                item.wdata & 0xFFFFFFFF
            )

        # Invalid address:
        # Ignore write (matches RTL)

    # ==========================================================
    # READ check
    # ==========================================================

    def _check_read(self, item):

        valid = 0 <= item.addr < 4

        expected_rresp = (
            self.OKAY if valid else self.SLVERR
        )

        expected_rdata = (
            self.regfile[item.addr]
            if valid
            else self.RESET_INVALID_RDATA
        )

        assert item.rresp == expected_rresp, (
            f"RRESP mismatch on READ: "
            f"addr={item.addr}, "
            f"expected={expected_rresp:#04b}, "
            f"got={item.rresp:#04b}"
        )

        assert item.rdata == expected_rdata, (
            f"RDATA mismatch on READ: "
            f"addr={item.addr}, "
            f"expected={expected_rdata:#010x}, "
            f"got={item.rdata:#010x}"
        )