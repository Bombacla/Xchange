from datetime import datetime

class Currency:
    """Represents a currency."""
    def __init__(self, code: str, name: str = None):
        self.code = code
        self.name = name

    def __repr__(self):
        return f"Currency(code='{self.code}', name='{self.name}')"

class ExchangeRate:
    """Represents an exchange rate between two currencies."""
    def __init__(self, base_currency_code: str, target_currency_code: str, rate: float, timestamp: datetime):
        self.base_currency_code = base_currency_code
        self.target_currency_code = target_currency_code
        self.rate = rate
        self.timestamp = timestamp

    def __repr__(self):
        return (f"ExchangeRate(base_currency_code='{self.base_currency_code}', "
                f"target_currency_code='{self.target_currency_code}', "
                f"rate={self.rate}, timestamp='{self.timestamp}')")

class AlertCondition:
    """Represents an alert condition for currency exchange rate changes."""
    def __init__(self, target_currency_code: str, percentage_drop_threshold: float, time_period_days: int):
        self.target_currency_code = target_currency_code
        self.percentage_drop_threshold = percentage_drop_threshold
        self.time_period_days = time_period_days

    def __repr__(self):
        return (f"AlertCondition(target_currency_code='{self.target_currency_code}', "
                f"percentage_drop_threshold={self.percentage_drop_threshold}, "
                f"time_period_days={self.time_period_days})")
