import cocotb
from pyuvm import uvm_monitor, uvm_analysis_port
from cocotb.triggers import RisingEdge, ReadOnly

from tb.sequences.sequence_item import AXISeqItem


class AXIMonitor(uvm_monitor):
    """
    Passively observes the AXI4-Lite bus and publishes one
    AXISeqItem per completed transaction.

    Detection is based on the rising edge of VALID rather than
    sampling VALID && READY together.
    """

    def build_phase(self):
        self.dut = cocotb.top
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):

        # Previous VALID values
        prev_awvalid = 0
        prev_wvalid = 0
        prev_bvalid = 0
        prev_arvalid = 0
        prev_rvalid = 0

        # Pending transaction information
        txn_type = None
        pending_addr = None
        pending_wdata = None

        while True:

            await RisingEdge(self.dut.ACLK)
            await ReadOnly()

            # ---------------------------------------------
            # Sample bus signals
            # ---------------------------------------------
            awvalid = int(self.dut.AWVALID.value)
            wvalid = int(self.dut.WVALID.value)
            bvalid = int(self.dut.BVALID.value)
            arvalid = int(self.dut.ARVALID.value)
            rvalid = int(self.dut.RVALID.value)

            awaddr = int(self.dut.AWADDR.value)
            wdata = int(self.dut.WDATA.value)
            bresp = int(self.dut.BRESP.value)

            araddr = int(self.dut.ARADDR.value)
            rdata = int(self.dut.RDATA.value)
            rresp = int(self.dut.RRESP.value)

            # ---------------------------------------------
            # Detect rising edges
            # ---------------------------------------------
            aw_rise = (awvalid == 1 and prev_awvalid == 0)
            w_rise = (wvalid == 1 and prev_wvalid == 0)
            b_rise = (bvalid == 1 and prev_bvalid == 0)

            ar_rise = (arvalid == 1 and prev_arvalid == 0)
            r_rise = (rvalid == 1 and prev_rvalid == 0)

            # =============================================
            # WRITE Transaction
            # =============================================

            if aw_rise:
                txn_type = "WRITE"
                pending_addr = awaddr

            if w_rise:
                pending_wdata = wdata

            if b_rise and txn_type == "WRITE":

                item = AXISeqItem("observed")

                item.txn_type = "WRITE"
                item.addr = pending_addr
                item.wdata = pending_wdata
                item.bresp = bresp

                self.ap.write(item)

                print(
                    f"[MONITOR] WRITE published "
                    f"addr={item.addr} "
                    f"wdata={item.wdata:#010x} "
                    f"bresp={item.bresp}"
                )

                txn_type = None
                pending_addr = None
                pending_wdata = None
            # =============================================
            # READ Transaction
            # =============================================

            if ar_rise:
                txn_type = "READ"
                pending_addr = araddr

            if r_rise and txn_type == "READ":

                item = AXISeqItem("observed")

                item.txn_type = "READ"
                item.addr = pending_addr
                item.rdata = rdata
                item.rresp = rresp

                self.ap.write(item)

                print(
                    f"[MONITOR] READ published "
                    f"addr={item.addr} "
                    f"rdata={item.rdata:#010x} "
                    f"rresp={item.rresp}"
                )

                txn_type = None
                pending_addr = None

            # ---------------------------------------------
            # Save current VALID values for next cycle
            # ---------------------------------------------
            prev_awvalid = awvalid
            prev_wvalid = wvalid
            prev_bvalid = bvalid

            prev_arvalid = arvalid
            prev_rvalid = rvalid                