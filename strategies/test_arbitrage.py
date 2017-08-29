import unittest
from unittest.mock import MagicMock, patch, call

from currency_graph import CurrencyGraph
from strategies.arbitrage import ArbitrageStrategy, MissingCurrencyGraph

class ArbitrageStrategyTestCase(unittest.TestCase):
    """
    Test :class:`ArbitrageStrategy`

    Methods:
        - :meth:`ArbitrageStrategy.next`
        - :meth:`ArbitrageStrategy._set_current_node`
        - :meth:`ArbitrageStrategy._track_order`
        - :meth:`ArbitrageStrategy._build_currency_graph`
        - :meth:`ArbitrageStrategy._get_currency_path`
        - :meth:`ArbitrageStrategy._get_market_price`
        - :meth:`ArbitrageStrategy._cancel_order`
        - :meth:`ArbitrageStrategy._update_pending_order`
        - :meth:`ArbitrageStrategy._place_order`
    """

    def test_next_place_new_order(self):
        """
        Test :meth:`ArbitrageStrategy.next`

        Assert :meth:`ArbitrageStrategy._place_order` is called and `True` is
        returned.
        """

        arbitrage = ArbitrageStrategy()

        trade_signal = (CurrencyGraph.BUY_ORDER, 'BTC-USD', 1.0,)
        arbitrage._get_trade_signal = MagicMock(return_value=trade_signal)

        arbitrage._set_current_node = MagicMock()
        arbitrage._track_order = MagicMock(return_value=False)
        arbitrage._update_pending_order = MagicMock()
        arbitrage._place_order = MagicMock()

        success = arbitrage.next()

        self.assertTrue(success)
        self.assertEqual(arbitrage._update_pending_order.called, 0)
        self.assertEqual(arbitrage._place_order.called, 1)

    def test_next_trade_signal_error(self):
        """
        Test :meth:`ArbitrageStrategy.next`

        Assert :meth:`ArbitrageStrategy._update_pending_order` and
        :meth:`ArbitrageStrategy._place_order` are not called and `False` is
        returned.
        """

        arbitrage = ArbitrageStrategy()

        error = MissingCurrencyGraph()
        arbitrage._get_trade_signal = MagicMock(side_effect=error)

        arbitrage._set_current_node = MagicMock()
        arbitrage._track_order = MagicMock(return_value=False)
        arbitrage._update_pending_order = MagicMock()
        arbitrage._place_order = MagicMock()

        success = arbitrage.next()

        self.assertFalse(success)
        self.assertEqual(arbitrage._update_pending_order.called, 0)
        self.assertEqual(arbitrage._place_order.called, 0)

    def test_next_update_pending_order(self):
        """
        Test :meth:`ArbitrageStrategy.next`

        Assert :meth:`ArbitrageStrategy._update_pending_order` is called and
        `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        trade_signal = (CurrencyGraph.BUY_ORDER, 'BTC-USD', 1.0,)
        arbitrage._get_trade_signal = MagicMock(return_value=trade_signal)

        arbitrage._set_current_node = MagicMock()
        arbitrage._track_order = MagicMock(return_value=True)
        arbitrage._update_pending_order = MagicMock()
        arbitrage._place_order = MagicMock()

        success = arbitrage.next()

        self.assertTrue(success)
        self.assertEqual(arbitrage._update_pending_order.called, 1)
        self.assertEqual(arbitrage._place_order.called, 0)

    def test__set_current_node_with_valid_balance(self):
        """
        Test :meth:`ArbitrageStrategy._set_current_node`

        Assert :attr:`ArbitrageStrategy.current_node` is set to the first
        account currency with a positive balance.
        """

        arbitrage = ArbitrageStrategy()

        UNCHANGED_NODE = 'FAKE'
        arbitrage.current_node = UNCHANGED_NODE

        TEST_CURRENCY = 'USD'
        TEST_2ND_CURRENCY = 'BTC'
        TEST_BALANCE = 1.0

        arbitrage.accounts = [
            {
                'currency': TEST_CURRENCY,
                'balance': TEST_BALANCE,
            }, {
                'currency': TEST_2ND_CURRENCY,
                'balance': TEST_BALANCE,
            }
        ]

        arbitrage._set_current_node()

        self.assertEqual(arbitrage.current_node, TEST_CURRENCY)

    def test__set_current_node_with_invalid_account_data(self):
        """
        Test :meth:`ArbitrageStrategy._set_current_node`

        Assert :attr:`ArbitrageStrategy.current_node` is unchanged.
        """

        arbitrage = ArbitrageStrategy()

        UNCHANGED_NODE = 'FAKE'
        arbitrage.current_node = UNCHANGED_NODE

        TEST_CURRENCY = 'USD'
        TEST_BALANCE = 1.0

        arbitrage.accounts = [
            { 'error': 'Invalid account data.', }
        ]

        arbitrage._set_current_node()

        self.assertEqual(arbitrage.current_node, UNCHANGED_NODE)

    def test__set_current_node_with_empty_balances(self):
        """
        Test :meth:`ArbitrageStrategy._set_current_node`

        Assert :attr:`ArbitrageStrategy.current_node` is unchanged.
        """

        arbitrage = ArbitrageStrategy()

        UNCHANGED_NODE = 'FAKE'
        arbitrage.current_node = UNCHANGED_NODE

        TEST_CURRENCY = 'USD'
        TEST_2ND_CURRENCY = 'BTC'
        TEST_BALANCE = 0.0

        arbitrage.accounts = [
            {
                'currency': TEST_CURRENCY,
                'balance': TEST_BALANCE,
            }, {
                'currency': TEST_2ND_CURRENCY,
                'balance': TEST_BALANCE,
            }
        ]

        arbitrage._set_current_node()

        self.assertEqual(arbitrage.current_node, UNCHANGED_NODE)

    def test__track_order_success(self):
        """
        Test :meth:`ArbitrageStrategy._track_order`

        Assert the current order data is updated and `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        test_order = {
            'id': 1,
        }
        arbitrage.order = test_order

        trader = MagicMock()

        test_order_update = {
            'id': 2,
        }
        trader.get_order.return_value = test_order_update

        arbitrage.trader = trader

        success = arbitrage._track_order()

        self.assertTrue(success)
        self.assertEqual(arbitrage.order, test_order_update)

    def test__track_order_with_no_current_order(self):
        """
        Test :meth:`ArbitrageStrategy._track_order`

        Assert `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        arbitrage.order = None

        trader = MagicMock()

        test_order_update = {
            'id': 2,
        }
        trader.get_order.return_value = test_order_update

        arbitrage.trader = trader

        success = arbitrage._track_order()

        self.assertFalse(success)
        self.assertEqual(arbitrage.order, None)

    def test__track_order_that_has_been_cancelled(self):
        """
        Test :meth:`ArbitrageStrategy._track_order`

        Assert the current order data is cleared and `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        test_order = {
            'id': 1,
        }
        arbitrage.order = test_order

        trader = MagicMock()

        test_order_update = {
            'id': 2,
            'done_reason': 'cancelled',
        }
        trader.get_order.return_value = test_order_update

        arbitrage.trader = trader

        success = arbitrage._track_order()

        self.assertFalse(success)
        self.assertEqual(arbitrage.order, None)

    def test__track_order__that_has_been_filled(self):
        """
        Test :meth:`ArbitrageStrategy._track_order`

        Assert the current order data is cleared and `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        test_order = {
            'id': 1,
        }
        arbitrage.order = test_order

        trader = MagicMock()

        test_order_update = {
            'id': 2,
            'status': 'done',
            'settled': True,
        }
        trader.get_order.return_value = test_order_update

        arbitrage.trader = trader

        success = arbitrage._track_order()

        self.assertFalse(success)
        self.assertEqual(arbitrage.order, None)

    @patch('strategies.arbitrage.CurrencyGraph')
    def test__build_currency_graph_with_valid_ticker_data(self, currency_graph_mock):
        """
        Test :meth:`ArbitrageStrategy._build_currency_graph`

        Assert currency pairs for every product are added to the graph and a
        non-`None` value is returned.
        """

        arbitrage = ArbitrageStrategy()

        trader = MagicMock()

        TEST_PRODUCT = 'BTC-USD'
        trader.products = [TEST_PRODUCT]
        arbitrage.trader = trader

        ticker = {
            TEST_PRODUCT: {
                'bid': 1.0,
                'ask': 1.0,
            },
        }
        arbitrage.ticker = ticker

        currency_graph = arbitrage._build_currency_graph()

        calls = []

        for product in ticker:
            base = CurrencyGraph.get_base(product)
            quote = CurrencyGraph.get_quote(product)
            bid = ticker[product]['bid']
            ask = ticker[product]['ask']
            calls.append(call().add_currency_pair(base, quote, bid, ask))

        currency_graph_mock.assert_has_calls(calls, any_order=True)

        self.assertNotEqual(currency_graph, None)

    @patch('strategies.arbitrage.CurrencyGraph')
    def test__build_currency_graph_with_missing_ticker_data(self, currency_graph_mock):
        """
        Test :meth:`ArbitrageStrategy._build_currency_graph`

        Assert `None` is returned when invalid ticker data is detected.
        """

        arbitrage = ArbitrageStrategy()

        trader = MagicMock()

        TEST_PRODUCT = 'BTC-USD'
        trader.products = [TEST_PRODUCT]
        arbitrage.trader = trader

        ticker = {
            TEST_PRODUCT: {
                'bid': 1.0,
            },
        }
        arbitrage.ticker = ticker

        currency_graph = arbitrage._build_currency_graph()

        self.assertEqual(currency_graph, None)

    def test__get_currency_path_with_currency_graph(self):
        """
        Test :meth:`ArbitrageStrategy._get_currency_path`

        Assert the tuple output of :meth:`CurrencyGraph.find_arbitrage_path`
        is returned.
        """

        arbitrage = ArbitrageStrategy()

        currency_graph = MagicMock()

        test_path = ['USD_bid', 'BTC_ask', 'BTC_bid', 'USD_ask']
        TEST_DISTANCE = 1.0
        currency_graph.find_arbitrage_path.return_value = (test_path, TEST_DISTANCE,)

        path, distance = arbitrage._get_currency_path(currency_graph)

        self.assertEqual(path, test_path)
        self.assertEqual(distance, TEST_DISTANCE)

    def test__get_currency_path_without_currency_graph(self):
        """
        Test :meth:`ArbitrageStrategy._get_currency_path`

        Assert that a :class:`MissingCurrencyGraph` exception is raised.
        """

        arbitrage = ArbitrageStrategy()

        currency_graph = MagicMock()

        currency_graph.find_arbitrage_path.side_effect = AttributeError

        with self.assertRaises(MissingCurrencyGraph):
            path, distance = arbitrage._get_currency_path(currency_graph)

    def test__get_market_price_with_no_signal(self):
        """
        Test :meth:`ArbitrageStrategy._get_market_price`

        Assert the returned market price is the same as the current order
        price.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage.order = {
            'price': TEST_PRICE,
        }

        TEST_PRODUCT = 'USD'
        TEST_BID = 2.0
        TEST_ASK = 3.0
        arbitrage.ticker = {
            TEST_PRODUCT: {
                'bid': TEST_BID,
                'ask': TEST_ASK,
            },
        }

        INVALID_SIGNAL = 3
        market_price = arbitrage._get_market_price(INVALID_SIGNAL, TEST_PRODUCT)

        self.assertEqual(market_price, TEST_PRICE)

    def test__get_market_price_with_no_order_and_no_signal(self):
        """
        Test :meth:`ArbitrageStrategy._get_market_price`

        Assert the returned market price is `None`.
        """

        arbitrage = ArbitrageStrategy()

        arbitrage.order = None

        TEST_PRODUCT = 'USD'
        TEST_BID = 2.0
        TEST_ASK = 3.0
        arbitrage.ticker = {
            TEST_PRODUCT: {
                'bid': TEST_BID,
                'ask': TEST_ASK,
            },
        }

        INVALID_SIGNAL = 3
        market_price = arbitrage._get_market_price(INVALID_SIGNAL, TEST_PRODUCT)

        self.assertEqual(market_price, None)

    def test__get_market_price_with_buy_signal(self):
        """
        Test :meth:`ArbitrageStrategy._get_market_price`

        Assert the returned market price is the ticker bid price.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage.order = {
            'price': TEST_PRICE,
        }

        TEST_PRODUCT = 'USD'
        TEST_BID = 2.0
        TEST_ASK = 3.0
        arbitrage.ticker = {
            TEST_PRODUCT: {
                'bid': TEST_BID,
                'ask': TEST_ASK,
            },
        }

        market_price = arbitrage._get_market_price(CurrencyGraph.BUY_ORDER, TEST_PRODUCT)

        self.assertEqual(market_price, TEST_BID)

    def test__get_market_price_with_sell_signal(self):
        """
        Test :meth:`ArbitrageStrategy._get_market_price`

        Assert the returned market price is the ticker ask price.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage.order = {
            'price': TEST_PRICE,
        }

        TEST_PRODUCT = 'USD'
        TEST_BID = 2.0
        TEST_ASK = 3.0
        arbitrage.ticker = {
            TEST_PRODUCT: {
                'bid': TEST_BID,
                'ask': TEST_ASK,
            },
        }

        market_price = arbitrage._get_market_price(CurrencyGraph.SELL_ORDER, TEST_PRODUCT)

        self.assertEqual(market_price, TEST_ASK)

    def test__get_market_price_with_invalid_ticker_data(self):
        """
        Test :meth:`ArbitrageStrategy._get_market_price`

        Assert the returned market price is the same as the current order
        price.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage.order = {
            'price': TEST_PRICE,
        }

        TEST_PRODUCT = 'USD'
        TEST_BID = 2.0
        TEST_ASK = 3.0
        arbitrage.ticker = {
            TEST_PRODUCT: {
                'error': 'Invalid ticker data.',
            },
        }

        market_price = arbitrage._get_market_price(CurrencyGraph.BUY_ORDER, TEST_PRODUCT)

        self.assertEqual(market_price, TEST_PRICE)

    def test__cancel_order_with_valid_order(self):
        """
        Test :meth:`ArbitrageStrategy._cancel_order`

        Assert :meth:`GDAXTrader.cancel_order` is called with current order ID
        and `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_ID = 1
        arbitrage.order = {
            'order_id': TEST_ID,
        }

        trader = MagicMock()
        arbitrage.trader = trader

        success = arbitrage._cancel_order()

        trader.cancel_order.assert_called_with(TEST_ID)
        self.assertTrue(success)

    def test__cancel_order_without_order(self):
        """
        Test :meth:`ArbitrageStrategy._cancel_order`

        Assert `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        arbitrage.order = None

        trader = MagicMock()
        arbitrage.trader = trader

        success = arbitrage._cancel_order()

        self.assertFalse(success)

    def test__update_pending_order_with_no_change(self):
        """
        Test :meth:`ArbitrageStrategy._update_pending_order`

        Assert :meth:`ArbitrageStrategy._cancel_order` is not called and
        `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRODUCT = 'BTC-USD'
        TEST_PRICE = 1.0
        arbitrage.order = {
            'product_id': TEST_PRODUCT,
            'price': TEST_PRICE,
        }

        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        cancel_order = MagicMock()
        arbitrage._cancel_order = cancel_order

        success = arbitrage._update_pending_order(CurrencyGraph.BUY_ORDER,
                TEST_PRODUCT)

        self.assertEqual(cancel_order.called, 0)
        self.assertTrue(success)

    def test__update_pending_order_without_order(self):
        """
        Test :meth:`ArbitrageStrategy._update_pending_order`

        Assert :meth:`ArbitrageStrategy._cancel_order` is not called and
        `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRODUCT = 'BTC-USD'
        TEST_PRICE = 1.0
        arbitrage.order = None

        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        cancel_order = MagicMock()
        arbitrage._cancel_order = cancel_order

        success = arbitrage._update_pending_order(CurrencyGraph.BUY_ORDER,
                TEST_PRODUCT)

        self.assertEqual(cancel_order.called, 0)
        self.assertFalse(success)

    def test__update_pending_order_with_change(self):
        """
        Test :meth:`ArbitrageStrategy._update_pending_order`

        Assert :meth:`ArbitrageStrategy._cancel_order` is called and `True`
        is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRODUCT = 'BTC-USD'
        TEST_PRICE = 1.0
        arbitrage.order = {
            'product_id': TEST_PRODUCT,
            'price': TEST_PRICE,
        }

        NEW_PRICE = 2.0
        arbitrage._get_market_price = MagicMock(return_value=NEW_PRICE)

        cancel_order = MagicMock()
        arbitrage._cancel_order = cancel_order

        success = arbitrage._update_pending_order(CurrencyGraph.BUY_ORDER,
                TEST_PRODUCT)

        self.assertEqual(cancel_order.called, 1)
        self.assertTrue(success)

    def test__place_order_below_threshold(self):
        """
        Test :meth:`ArbitrageStrategy._place_order`

        Assert that no orders are placed and `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        arbitrage.get_currency_balance = MagicMock()

        trader = MagicMock()
        arbitrage.trader = trader

        TEST_SIGNAL = CurrencyGraph.BUY_ORDER
        TEST_PRODUCT = 'BTC-USD'
        TEST_DISTANCE = 1.0

        success = arbitrage._place_order(TEST_SIGNAL, TEST_PRODUCT,
                TEST_DISTANCE)

        self.assertEqual(trader.buy.called, 0)
        self.assertEqual(trader.sell.called, 0)
        self.assertFalse(success)

    def test__place_order_buy_signal(self):
        """
        Test :meth:`ArbitrageStrategy._place_order`

        Assert a buy order is placed and `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        arbitrage.get_currency_balance = MagicMock()

        trader = MagicMock()
        arbitrage.trader = trader

        TEST_SIGNAL = CurrencyGraph.BUY_ORDER
        TEST_PRODUCT = 'BTC-USD'
        TEST_DISTANCE = 2.0

        success = arbitrage._place_order(TEST_SIGNAL, TEST_PRODUCT,
                TEST_DISTANCE)

        self.assertEqual(trader.buy.called, 1)
        self.assertEqual(trader.sell.called, 0)
        self.assertTrue(success)

    def test__place_order_sell_signal(self):
        """
        Test :meth:`ArbitrageStrategy._place_order`

        Assert a sell order is placed and `True` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        arbitrage.get_currency_balance = MagicMock()

        trader = MagicMock()
        arbitrage.trader = trader

        TEST_SIGNAL = CurrencyGraph.SELL_ORDER
        TEST_PRODUCT = 'BTC-USD'
        TEST_DISTANCE = 2.0

        success = arbitrage._place_order(TEST_SIGNAL, TEST_PRODUCT,
                TEST_DISTANCE)

        self.assertEqual(trader.buy.called, 0)
        self.assertEqual(trader.sell.called, 1)
        self.assertTrue(success)

    def test__place_order_invalid_signal(self):
        """
        Test :meth:`ArbitrageStrategy._place_order`

        Assert that no orders are placed and `False` is returned.
        """

        arbitrage = ArbitrageStrategy()

        TEST_PRICE = 1.0
        arbitrage._get_market_price = MagicMock(return_value=TEST_PRICE)

        arbitrage.get_currency_balance = MagicMock()

        trader = MagicMock()
        arbitrage.trader = trader

        INVALID_SIGNAL = 3
        TEST_PRODUCT = 'BTC-USD'
        TEST_DISTANCE = 2.0

        success = arbitrage._place_order(INVALID_SIGNAL, TEST_PRODUCT,
                TEST_DISTANCE)

        self.assertEqual(trader.buy.called, 0)
        self.assertEqual(trader.sell.called, 0)
        self.assertFalse(success)
