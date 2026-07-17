import cocotb
from pyuvm import uvm_driver
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep


class AXIDriver(uvm_driver):
    """
    Drives WRITE and READ transactions onto an AXI4-Lite slave using
    standard, RTL-agnostic master handshake behavior.

    Two reusable primitives, one per channel role:

    _drive_source() -- used for AW, W, AR (driver is the source):
        S0: drive the payload, then assert VALID unconditionally
            (independent of READY).

        S1: sample READY's current (pre-edge) value, then await the
            next clock edge.

            - if READY was already 1 going into that edge, the
              handshake occurred AT that edge (our VALID was held
              through it) -> deassert VALID, done.

            - otherwise, VALID and the payload remain untouched
              (never withdrawn early) -> resample on the next edge.

    _drive_dest() -- used for B, R (driver is the destination):

        D0: poll until VALID is observed asserted, sampling VALID
            and the payload together in the same read-only snapshot
            each cycle (avoids any race between "is it valid" and
            "what does it say").

        D1: once VALID is seen, the just-sampled payload is already
            guaranteed stable and correct -- no separate capture step
            needed.

        D2: assert READY, complete the handshake on the following
            edge, deassert READY.

    This is a deliberate, fixed one-cycle response delay (READY
    only rises after VALID is confirmed), not an accidental one:
    it exercises the slave's must-hold-VALID-and-payload-stable
    obligation on every single transaction, which is exactly the
    property the RDATA/RRESP latch fix in the RTL was added to
    guarantee. An always-ready destination would never exercise
    that path at all.

    Neither primitive references any state name, cycle count, or
    other implementation detail of a specific slave -- both rely only
    on the standard AXI4-Lite READY/VALID contract, so this driver
    works against any compliant slave implementing this signal subset
    (no WSTRB/AWPROT/ARPROT), not just the current RTL.
    """

    def build_phase(self):
        self.dut = cocotb.top

    async def run_phase(self):
        # ------------------------------------------------------
        # Reset sequencing (driver-owned, matches prior convention).
        # ARESETN is active-low.
        # ------------------------------------------------------
        self.dut.ARESETN.value = 0
        self.dut.AWVALID.value = 0
        self.dut.AWADDR.value = 0
        self.dut.WVALID.value = 0
        self.dut.WDATA.value = 0
        self.dut.BREADY.value = 0
        self.dut.ARVALID.value = 0
        self.dut.ARADDR.value = 0
        self.dut.RREADY.value = 0

        for _ in range(2):
            await RisingEdge(self.dut.ACLK)

        self.dut.ARESETN.value = 1
        await RisingEdge(self.dut.ACLK)

        # ------------------------------------------------------
        # Main transaction loop
        # ------------------------------------------------------
        while True:
            item = await self.seq_item_port.get_next_item()

            if item.txn_type == "WRITE":
                await self._do_write(item)
            else:
                await self._do_read(item)

            self.seq_item_port.item_done()

    # ==========================================================
    # WRITE: AW (source) -> W (source) -> B (destination)
    # ==========================================================

    async def _do_write(self, item):
        await self._drive_source(
            valid_signal=self.dut.AWVALID,
            ready_signal=self.dut.AWREADY,
            payload={
                self.dut.AWADDR: item.addr & 0xFF,
            },
        )

        await self._drive_source(
            valid_signal=self.dut.WVALID,
            ready_signal=self.dut.WREADY,
            payload={
                self.dut.WDATA: item.wdata & 0xFFFFFFFF,
            },
        )

        (item.bresp,) = await self._drive_dest(
            valid_signal=self.dut.BVALID,
            ready_signal=self.dut.BREADY,
            capture_signals=[
                self.dut.BRESP,
            ],
        )

    # ==========================================================
    # READ: AR (source) -> R (destination)
    # ==========================================================

    async def _do_read(self, item):
        await self._drive_source(
            valid_signal=self.dut.ARVALID,
            ready_signal=self.dut.ARREADY,
            payload={
                self.dut.ARADDR: item.addr & 0xFF,
            },
        )

        item.rdata, item.rresp = await self._drive_dest(
            valid_signal=self.dut.RVALID,
            ready_signal=self.dut.RREADY,
            capture_signals=[
                self.dut.RDATA,
                self.dut.RRESP,
            ],
        )

    # ==========================================================
    # Reusable channel-role primitives
    # ==========================================================
    async def _drive_source(self, valid_signal, ready_signal, payload):
        """
        Standard AXI4-Lite SOURCE handshake (used for AW/W/AR).

        Drives the payload, asserts VALID independently of READY,
        holds both stable until a READY/VALID coincidence is
        observed, then deasserts VALID. RTL-agnostic: relies only on
        READY being a stable, sampleable signal between edges.
        """

        for sig, val in payload.items():
            sig.value = val

        valid_signal.value = 1

        while True:
            (ready_now,) = await self._sample(ready_signal)

            await RisingEdge(self.dut.ACLK)

            if ready_now == 1:
                valid_signal.value = 0
                return

    async def _drive_dest(
        self,
        valid_signal,
        ready_signal,
        capture_signals,
    ):
        """
        Standard AXI4-Lite DESTINATION handshake (used for B/R).

        Waits for VALID, capturing VALID and the payload together in
        the same read-only snapshot each cycle (so there is no
        window where VALID could be checked and the payload read at
        different, inconsistent times).

        Once VALID is seen, asserts READY, completes the handshake
        on the following edge, then deasserts READY.

        Returns the captured payload values.
        """

        print(f"[DRIVER] Waiting for {valid_signal._name}")

        while True:
            v, *values = await self._sample(
                valid_signal,
                *capture_signals,
            )

            if v == 1:
                print(f"[DRIVER] {valid_signal._name} observed HIGH")
                break

            await RisingEdge(self.dut.ACLK)

        print(f"[DRIVER] Asserting {ready_signal._name}")
        print(f"[DRIVER] {ready_signal._name}=1")

        ready_signal.value = 1

        await RisingEdge(self.dut.ACLK)

        print(f"[DRIVER] AFTER EDGE")
        print(f"[DRIVER] Deasserting {ready_signal._name}")

        ready_signal.value = 0

        print(f"[DRIVER] {ready_signal._name}=0")

        return values

    # ==========================================================
    # Low-level sampling helper
    # ==========================================================

    async def _sample(self, *signals):
        """
        Safely read one or more DUT output signals:

        - Sync to the ReadOnly phase (guaranteeing this cycle's
          NBA updates have settled).

        - Then advance past it via NextTimeStep so that any
          subsequent `.value =` write in the caller is legal again.
        """

        await ReadOnly()

        values = [int(s.value) for s in signals]

        await NextTimeStep()

        return values