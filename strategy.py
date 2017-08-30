import logging


logger = logging.getLogger(__name__)


class Strategy:
    """
    Base class for trading strategy implementations

    Attributes:
        trader: An instance of :class:`GDAXTrader`.
        accounts: GDAX account data
        ticker: GDAX ticker data for all products
        orders: GDAX order data
        position: GDAX profile overview
    """

    def __init__(self):
        self.trader = None

        self.set_up()

    def set_up(self):
        """
        Override in child class to run code on initialization
        """

        pass

    def add_trader(self, trader):
        self.trader = trader

    def next(self):
        """
        Must be implemented by child class

        Strategy logic goes in this method.

        The instance variable dictionaries available to strategies have the
        following fields:

            accounts:
                - id
                - currency
                - balance
                - available
                - hold
                - profile_id

            ticker:
                - trade_id
                - price
                - size
                - bid
                - ask
                - volume
                - time

            orders:
                - id
                - price
                - size
                - product_id
                - side
                - stp
                - type
                - time_in_force
                - post_only
                - created_at
                - fill_fees
                - filled_size
                - executed_value
                - status
                - settled

            position:
                - status
                - funding
                - accounts
                - margin_call
                - user_id
                - profile_id
                - position
                     - type
                     - size
                     - complement
                     - max_size
                - product_id
        """

        raise NotImplementedError

    def next_data(self, accounts, ticker, orders, position):
        """
        Set data to be used for the current strategy iteration

        :param accounts: accounts data
        :param ticker: ticker data
        :param orders: order data
        :param position: position data
        """

        self.accounts = accounts
        self.ticker = ticker
        self.orders = orders
        self.position = position

    def get_currency_balance(self, currency):
        """
        Get the current account balance for a currency

        `None` is returned when the currency does not exist.

        :param currency: the currency to get the balance for
        :returns: the balance of the account
        """

        for account in self.accounts:
            try:
                if account['currency'] == currency:
                    return float(account['balance'])
            except (KeyError, TypeError, ValueError):
                continue

        return None
