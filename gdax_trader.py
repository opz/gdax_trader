import logging
import os

from requests.exceptions import ConnectionError

import gdax

from utils import connection_retry


logger = logging.getLogger(__name__)


class GDAXTrader:
    """
    Run trading strategy and interact with GDAX API

    Attributes:
        products: The products being tracked by the trader
        strategies: The strategies being run by the trader
        client: The GDAX API client
    """

    # Environment variables required for authenticating with GDAX
    GDAX_KEY_ENV = 'GDAX_KEY'
    GDAX_SECRET_ENV = 'GDAX_SECRET'
    GDAX_PASSPHRASE_ENV = 'GDAX_PASSPHRASE'
    GDAX_API_URL_ENV = 'GDAX_API_URL'

    # GDAX rate limit of 3 requests per second with a little extra padding
    RATE_LIMIT = 1.0 / 3.0 + 0.5

    # Maximum number of retry attempts after a connection error
    MAX_RETRIES = 5

    def __init__(self):
        self.products = []
        self.strategies = []
        self.client = GDAXTrader._get_client()

    def add_product(self, product):
        self.products.append(product)

    def add_strategy(self, strategy):
        strategy.add_trader(self)
        self.strategies.append(strategy)

    def run(self):
        """
        Start the GDAX trading algorithm

        Uses all products and strategies added to the `GDAXTrader`.
        """

        running = True

        logger.info('Starting GDAX Trader...')

        while running:
            success = self._run_iteration()

            if not success:
                logger.warning('Data unavailable, iteration skipped...')

    def _run_iteration(self):
        """
        Perform an iteration of the GDAX trading algorithm
        """

        # Retrieve all trading data
        try:
            accounts = self._get_accounts()
            orders = self._get_orders()
            position = self._get_position()

        # Skip iteration if trading data is unavailable
        except ConnectionError:
            return False

        tick_data = {}

        # Get all product ticker data
        for product in self.products:
            try:
                tick_data[product] = self._get_product_ticker(product)

            # Skip iteration if ticker data is unavailable
            except ConnectionError:
                return False

        # Update all strategies
        for strategy in self.strategies:
            logger.info('Next iteration...')
            strategy.next_data(accounts, tick_data, orders, position)
            strategy.next()

        return True

    @classmethod
    def _get_client(cls):
        """
        Get an authenticated GDAX client

        :returns: an authenticated GDAX client
        :raises KeyError: Error raised if environment variables are not set
        """

        try:
            key = os.environ[GDAXTrader.GDAX_KEY_ENV]
            secret = os.environ[GDAXTrader.GDAX_SECRET_ENV]
            passphrase = os.environ[GDAXTrader.GDAX_PASSPHRASE_ENV]
        except KeyError as error:
            raise KeyError('Missing environment variable for GDAX: '.format(error))

        try:
            api_url = os.environ[GDAXTrader.GDAX_API_URL_ENV]
        except KeyError:
            client = gdax.AuthenticatedClient(key, secret, passphrase)
        else:
            client = gdax.AuthenticatedClient(key, secret, passphrase,
                    api_url=api_url)

        return client

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def _get_product_ticker(self, product):
        """
        Get ticker data for a product

        :param product: the GDAX product
        :returns: ticker data
        """

        return self.client.get_product_ticker(product_id=product)

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def _get_accounts(self):
        """
        Get accounts data

        :returns: accounts data
        """

        return self.client.get_accounts()

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def _get_orders(self):
        """
        Get orders

        :returns: list of orders
        """

        return self.client.get_orders()

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def _get_position(self):
        """
        Get positions

        :returns: get a profile overview
        """

        return self.client.get_position()

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def get_order(self, order_id):
        """
        Get a single order

        :param order_id: the order ID
        :returns: the order
        """

        return self.client.get_order(order_id)

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def get_fills(self, order_id):
        """
        Get fills for an order

        :param order_id: the order ID
        :returns: list of fills
        """

        return self.client.get_fills(order_id=order_id)

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def buy(self, price, size, product):
        """
        Place buy order for a product

        :param price: the maximum price that will be accepted
        :size: the amount to buy
        :product: the product to place the buy order for
        :returns: order data
        """

        logger.info('BUY: {} of {}, PRICE: {}'.format(size, product, price))
        return self.client.buy(price=price, size=size, product_id=product,
                time_in_force='FOK')

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def sell(self, price, size, product):
        """
        Place sell order for a product

        :param price: the minimum price that will be accepted
        :size: the amount to sell
        :product: the product to place the sell order for
        :returns: order data
        """

        logger.info('SELL: {} of {}, PRICE: {}'.format(size, product, price))
        return self.client.sell(price=price, size=size, product_id=product,
                time_in_force='FOK')

    @connection_retry(MAX_RETRIES, RATE_LIMIT)
    def cancel_order(self, order_id):
        """
        Cancel an order

        :param order_id: the order ID
        :returns: the API response
        """

        logger.info('CANCEL: {}'.format(order_id))
        return self.client.cancel_order(order_id)
