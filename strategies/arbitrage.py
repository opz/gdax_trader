from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import logging

from currency_graph import CurrencyGraph
from strategy import Strategy


logger = logging.getLogger(__name__)


class MissingCurrencyGraph(Exception):
    """
    Raise when expecting a currency graph that does not exist
    """

    pass


class ArbitrageStrategy(Strategy):
    """
    Find arbitrage opportunities in a graph of currency pairs

    Attributes:
        current_node: The currency node the currency path starts from
        orders: The currently open orders for each account
    """

    START_NODE = 'USD' # the default start currency
    TARGET_NODE = 'USD' # the target currency

    THRESHOLD = 1.002 # the minimum spread required to start a trade

    def set_up(self):
        self.current_node = ArbitrageStrategy.START_NODE
        self.orders = {}

    def next(self):
        for account in self.accounts:
            # Set the current node
            try:
                current_node = account['currency']

                logger.info('Checking {} account'.format(current_node))

                balance = Decimal(account['balance'])
            except (KeyError, TypeError, InvalidOperation):
                continue

            logger.info('Balance is {}'.format(balance))

            if balance > Decimal(0):
                self.current_node = current_node

                logger.info('Current node is {}'.format(self.current_node))

                # Get the trade signal for the current node
                try:
                    signal, product, distance = self._get_trade_signal()
                except MissingCurrencyGraph as error:
                    logger.warning(error)
                    continue

                logger.info('Next trade signal: {} {} {}'.format(signal, product,
                        distance))

                # Update open orders
                if self._track_order():
                    logger.info('Update pending order...')
                    self._update_pending_order(signal, product)
                    continue

                logger.info('ORDERS: {}'.format(self.orders))

                logger.info('Place new order...')
                self._place_order(signal, product, distance)

    def _track_order(self):
        """
        Track the order if it is available

        Updates the current order with new data, or clears the current order
        if it no longer exists.

        :returns: `True` if the order has updated, `False` if it does not exist
        """

        try:
            order_id = self.orders[self.current_node]['id']
        except (KeyError, TypeError):
            return False

        try:
            order = self.trader.get_order(order_id)
        except ConnectionError as error:
            logger.warning(error)
            return False

        # Check if a partially filled order has been cancelled
        try:
            cancelled = order['done_reason'] == 'cancelled'
        except KeyError:
            cancelled = False

        try:
            rejected = order['status'] == 'rejected'
        except KeyError:
            rejected = False

        # Check if order has been completed
        try:
            is_done = order['status'] == 'done'
        except KeyError:
            is_done = False

        # Check if order has been settled
        try:
            is_settled = order['settled'] == True
        except KeyError:
            is_settled = False

        # An unfilled order that was cancelled will throw an error
        order_error = 'message' in order

        # Clear the order if it no longer exists or has been cancelled
        if order_error or cancelled or rejected or (is_done and is_settled):
            self.orders[self.current_node] = None
            return False
        else:
            self.orders[self.current_node] = order

        return True

    def _build_currency_graph(self):
        """
        Build the currency graph using ticker data

        :returns: the currency graph
        """

        currency_graph = CurrencyGraph()

        for product in self.trader.products:
            currency_pair = product.split('-')

            base = currency_pair[0]
            quote = currency_pair[1]

            try:
                bid = Decimal(self.ticker[product]['bid'])
                ask = Decimal(self.ticker[product]['ask'])

            # Do not build graph if ticker data is missing
            except (KeyError, InvalidOperation) as error:
                logger.warning(error)
                return None

            currency_graph.add_currency_pair(base, quote, bid, ask)

        return currency_graph

    def _get_currency_path(self, currency_graph):
        """
        Find the best path from the current node to the target node

        :param currency_graph: the currency_graph
        :results: tuple(path, distance)
            - the currency path
            - the distance to the target currency
        :raises MissingCurrencyGraph: currency graph parameter is invalid
        """

        start = CurrencyGraph.get_bid(self.current_node)

        target = CurrencyGraph.get_ask(ArbitrageStrategy.TARGET_NODE)

        try:
            path, distance = currency_graph.find_arbitrage_path(start, target)

        # Return None if currency_graph has not been initialized
        except AttributeError:
            error_msg = 'Expecting currency graph: {}'.format(currency_graph)
            raise MissingCurrencyGraph(error_msg)

        return path, distance

    def _get_trade_signal(self):
        """
        Get the Buy/Sell trade signal based on ticker data

        Return `None` values if the currency graph could not be built.

        :returns: tuple(trade_signal, currency_pair, distance)
            - trade_signal: either a buy or a sell signal
            - currency_pair: the currency pair that should be traded on
            - distance: the distance to the target node
        """

        currency_graph = self._build_currency_graph()

        path, distance = self._get_currency_path(currency_graph)

        logger.info('Best path for arbitrage: {}'.format(path))
        logger.info('Path distance: {}'.format(distance))

        return currency_graph.get_next_signal(path) + (distance,)

    def _get_market_price(self, signal, product):
        """
        Get the market price based on the trade signal for a product

        A buy signal uses the bid price, a sell signal uses the ask price.

        :param signal: the trade signal
        :param product: the product
        :returns: the market price
        """

        try:
            market_price = self.orders[self.current_node]['price']
        except (KeyError, TypeError):
            market_price = None

        try:
            if signal == CurrencyGraph.BUY_ORDER:
                market_price = Decimal(self.ticker[product]['bid'])

            elif signal == CurrencyGraph.SELL_ORDER:
                market_price = Decimal(self.ticker[product]['ask'])

        # Use existing order price if ticker data is invalid
        except (KeyError, InvalidOperation) as error:
            logger.warning(error)

        return market_price

    def _cancel_order(self):
        """
        Cancel the current order

        :returns: `True` if success, `False` if there is no current order
        """

        try:
            order_id = self.orders[self.current_node]['order_id']
        except (KeyError, TypeError):
            return False

        try:
            self.trader.cancel_order(order_id)
        except ConnectionError as error:
            logger.warning(error)
            return False

        return True

    def _update_pending_order(self, signal, product):
        """
        Make adjustments to a pending order based on new data

        Reprice the order if market conditions change and cancel the order if
        the trade signal changes.

        :param signal: the trade signal
        :param product: the product
        :returns: `True` on success, `False` when there is no pending order
        """

        try:
            product_id = self.orders[self.current_node]['product_id']
            price = Decimal(self.orders[self.current_node]['price'])
            created_at = self.orders[self.current_node]['created_at']
        except (KeyError, TypeError, InvalidOperation):
            return False

        same_product = product_id == product

        market_price = self._get_market_price(signal, product)

        timeframe = timedelta(minutes=1)
        created_at_dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        elapsed_time = current_time - created_at_dt

        logger.info('Time elapsed since order creation: {}'.format(elapsed_time))

        can_be_cancelled = elapsed_time > timeframe

        if can_be_cancelled and (not same_product or price != market_price):
            logger.info('Cancel pending order')
            self._cancel_order()
        else:
            logger.info('Pending order unchanged')

        return True

    def _place_order(self, signal, product, distance):
        """
        Place a new order based on the trade signal

        :param signal: the trade signal
        :param product: the product
        :param distance: the distance to the target currency
        :returns: `True` if order is placed, `False` if no order is placed
        """

        # Do not place a new order if an old order is still open
        try:
            if self.orders[self.current_node] != None:
                return False
        except KeyError:
            pass

        market_price = self._get_market_price(signal, product)

        spread = distance / market_price

        if spread > ArbitrageStrategy.THRESHOLD:
            logger.info('Trade signal above threshold: {}'.format(spread))

            if signal == CurrencyGraph.BUY_ORDER:
                logger.info('Signal indicates BUY order')

                currency = CurrencyGraph.get_quote(product)
                logger.info('BUY with {}'.format(currency))

                size = self.get_currency_balance(currency) / market_price
                logger.info('Size of position: {}'.format(size))

                try:
                    order = self.trader.buy(market_price, size, product)
                except ConnectionError as error:
                    logger.warning(error)
                    return False

                if 'message' not in order:
                    self.orders[self.current_node] = order

                return True

            elif signal == CurrencyGraph.SELL_ORDER:
                logger.info('Signal indicates SELL order')

                currency = CurrencyGraph.get_base(product)
                logger.info('SELL with {}'.format(currency))

                size = self.get_currency_balance(currency) * market_price
                logger.info('Size of position: {}'.format(size))

                try:
                    order = self.trader.sell(market_price, size, product)
                except ConnectionError as error:
                    logger.warning(error)
                    return False

                if 'message' not in order:
                    self.orders[self.current_node] = order

                return True

        logger.info('Trade signal below threshold: {}'.format(spread))

        return False
