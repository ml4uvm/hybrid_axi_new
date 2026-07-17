class CoverageGapAnalyzer:
    """
    Determines which functional coverage bins
    are still uncovered after ML execution.
    """

    def __init__(self, total_bins):
        self.total_bins = total_bins

    def get_uncovered_bins(self, covered_bins):
        """
        Returns a sorted list of uncovered bins.

        Parameters
        ----------
        covered_bins : iterable
            Collection of covered coverage bin IDs.

        Returns
        -------
        list
            Sorted uncovered coverage bin IDs.
        """
        covered = set(covered_bins)

        uncovered = []

        for bin_id in range(self.total_bins):
            if bin_id not in covered:
                uncovered.append(bin_id)

        return uncovered

    def coverage_complete(self, covered_bins):
        """
        Returns True when all bins have been covered.
        """
        return len(set(covered_bins)) >= self.total_bins
