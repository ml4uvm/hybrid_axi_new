from pyuvm import uvm_sequence_item
import random

# ============================================================
# Address / data category helpers
# ============================================================

VALID_REGS = [0, 1, 2, 3]

# REG0..REG3 addresses
ADDR_CATEGORIES = [
    "REG0",
    "REG1",
    "REG2",
    "REG3",
    "INVALID",
]

DATA_CATEGORIES = [
    "ZERO",
    "SMALL",
    "LARGE",
]


def random_invalid_addr():
    """Pick an 8-bit address outside the valid register range [0-3]."""
    return random.randint(4, 255)


def random_data_value(data_type):
    if data_type == "ZERO":
        return 0

    elif data_type == "SMALL":
        return random.randint(1, 9)

    elif data_type == "LARGE":
        return random.randint(10, 0xFFFFFFFF)

    raise ValueError(f"Unknown data_type: {data_type}")


class AXISeqItem(uvm_sequence_item):
    """
    Single transaction item for the AXI4-Lite offline framework.

    Represents either a WRITE or READ transaction.
    """

    def __init__(self, name="axi_seq_item"):
        super().__init__(name)

        # ----------------------------------------------------
        # Transaction type
        # ----------------------------------------------------
        self.txn_type = "WRITE"

        # ----------------------------------------------------
        # Stimulus fields
        # ----------------------------------------------------
        self.addr = 0
        self.wdata = 0

        # ----------------------------------------------------
        # Observed fields
        # ----------------------------------------------------
        self.rdata = 0
        self.bresp = 0
        self.rresp = 0

        # ----------------------------------------------------
        # ML label
        # ----------------------------------------------------
        self.data_type = "NA"

    # ==========================================================
    # Randomization
    # ==========================================================

    def randomize(self):
        """
        Balanced random testcase generation.

        First selects an address category uniformly, then chooses
        a concrete address from that category.
        """

        self.txn_type = random.choice(
            [
                "WRITE",
                "READ",
            ]
        )

        addr_cat = random.choice(ADDR_CATEGORIES)

        if addr_cat == "INVALID":
            self.addr = random_invalid_addr()

        else:
            self.addr = VALID_REGS[
                ADDR_CATEGORIES.index(addr_cat)
            ]

        if self.txn_type == "WRITE":

            if addr_cat == "INVALID":

                self.data_type = "NA"
                self.wdata = random.randint(
                    0,
                    0xFFFFFFFF,
                )

            else:

                self.data_type = random.choice(
                    DATA_CATEGORIES
                )

                self.wdata = random_data_value(
                    self.data_type
                )

        else:
            # READ transaction
            self.data_type = "NA"
            self.wdata = 0

        return True

    def __str__(self):
        return (
            f"AXISeqItem("
            f"txn_type={self.txn_type}, "
            f"addr={self.addr}, "
            f"wdata={self.wdata:#010x}, "
            f"rdata={self.rdata:#010x}, "
            f"bresp={self.bresp}, "
            f"rresp={self.rresp}, "
            f"data_type={self.data_type})"
        )