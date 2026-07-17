from tb.sequences.sequence_item import (
    AXISeqItem,
    random_invalid_addr,
    random_data_value,
)


class DirectedGenerator:
    """
    Generates deterministic AXI transactions
    for uncovered functional coverage bins.
    """

    def generate(self, bin_key):
        """
        Convert a coverage bin into an AXISeqItem.
        """

        item = AXISeqItem("directed_item")

        # -----------------------------
        # READ bins
        # -----------------------------
        if bin_key[0] == "READ":

            item.txn_type = "READ"

            addr_cat = bin_key[1]

            if addr_cat == "INVALID":
                item.addr = random_invalid_addr()
            else:
                item.addr = int(addr_cat[-1])   # REG0 -> 0

            item.wdata = 0
            item.data_type = "NA"

            return item

        # -----------------------------
        # WRITE bins
        # -----------------------------
        item.txn_type = "WRITE"

        addr_cat = bin_key[1]

        if addr_cat == "INVALID":

            item.addr = random_invalid_addr()
            item.wdata = random_data_value("LARGE")
            item.data_type = "NA"

            return item

        item.addr = int(addr_cat[-1])

        data_type = bin_key[2]

        item.data_type = data_type
        item.wdata = random_data_value(data_type)

        return item
