class BudgetManager:
    """
    Tracks the remaining directed-test execution budget.
    """

    def __init__(self, max_budget=20):
        self.max_budget = max_budget
        self.remaining_budget = max_budget

    def consume(self):
        """
        Consume one unit of budget.

        Returns True if execution may continue,
        False if budget has been exhausted.
        """
        if self.remaining_budget <= 0:
            return False

        self.remaining_budget -= 1
        return True

    def exhausted(self):
        """
        Returns True if no budget remains.
        """
        return self.remaining_budget <= 0

    def reset(self):
        """
        Reset budget for a new hybrid run.
        """
        self.remaining_budget = self.max_budget
