import cocotb

from pyuvm import uvm_test, uvm_root
from cocotb.clock import Clock

from tb.components.env import AXIEnv
from tb.sequences.sequence import AXISequence


class AXITest(uvm_test):

    def build_phase(self):
        self.env = AXIEnv("env", self)

    async def run_phase(self):
        self.raise_objection()

        # =====================================================
        # BASELINE MODE (CRV/CDV comparison)
        #
        # Budget matches the paper's testcase counts:
        #
        # 18 (1x)
        # 27 (1.5x)
        # 36 (2x)
        # 54 (3x)
        # 72 (4x)
        #
        # Uncomment this for baseline mode.
        # =====================================================

        # seq = AXISequence(
        #     "seq",
        #     num_tests=18,
        #     use_hybrid=False,
        # )

        # =====================================================
        # HYBRID MODE
        #
        # Offline Random Forest + KMeans clustered testcases.
        # =====================================================

        seq = AXISequence(
            "seq",
            total_budget=36,
            use_hybrid=True,
        )

        await seq.start(self.env.agent.seqr)

        self.drop_objection()


@cocotb.test()
async def run_test(dut):
    """
    Top-level cocotb test.

    Clock generation happens here.

    Reset sequencing is owned entirely by driver.py.
    """

    clock = Clock(
        dut.ACLK,
        10,
        unit="ns",
    )

    cocotb.start_soon(clock.start())

    await uvm_root().run_test("AXITest")