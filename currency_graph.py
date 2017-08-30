from decimal import Decimal
import math


class CurrencyGraph:
    """
    Analyze relationships between currencies

    After initializing an instance of :class:`CurrencyGraph`, the graph can be
    populated by calling :meth:`CurrencyGraph.add_currency_pair`.

    A populated graph can then run :meth:`CurrencyGraph.find_arbitrage_path`.
    This method finds the optimal path from a start to a target currency that
    creates the largest possible price spread for arbitrage.

    Trade signals can be generated by calling
    :meth:`CurrencyGraph.get_next_currency_pair` on the arbitrage path.

    Attributes:
        currency_pairs: list of currency pairs represented in the graph
        currency_graph: graph of currency relationships
    """

    BID_KEY = 'bid' # Bid node key suffix
    ASK_KEY = 'ask' # Ask node key suffix
    INDEX_FORMAT = '{}_{}' # Node key format
    BASE_KEY = 'base' # Currency pair base key
    QUOTE_KEY = 'quote' # Currency pair quote key

    BUY_ORDER = 1 # Buy order trade signal
    SELL_ORDER = 2 # Sell order trade signal

    def __init__(self):
        self.currency_pairs = []
        self.currency_graph = {}

    def add_currency_pair(self, base, quote, bid, ask):
        """
        Add a currency pair to the currency graph

        Two edges are a created between the pair of currencies, creating a
        bid / ask spread.

        :param base: base currency
        :param quote: quote currency
        :param bid: current bid price
        :param ask: current ask price
        """

        self.currency_pairs.append({
            CurrencyGraph.BASE_KEY: base,
            CurrencyGraph.QUOTE_KEY: quote
        })

        quote_bid = CurrencyGraph.INDEX_FORMAT.format(quote,
                CurrencyGraph.BID_KEY)
        base_ask = CurrencyGraph.INDEX_FORMAT.format(base,
                CurrencyGraph.ASK_KEY)

        quote_ask = CurrencyGraph.INDEX_FORMAT.format(quote,
                CurrencyGraph.ASK_KEY)
        base_bid = CurrencyGraph.INDEX_FORMAT.format(base,
                CurrencyGraph.BID_KEY)

        #
        # CONNECT BASE CURRENCY TO QUOTE CURRENCY
        #

        try:
            self.currency_graph[quote_bid][base_ask] = bid
        except KeyError:
            self.currency_graph[quote_bid] = { base_ask: bid }

        # Take reciprocal of ask price for reverse edge
        converted_ask = Decimal(1) / ask

        try:
            self.currency_graph[base_bid][quote_ask] = converted_ask
        except KeyError:
            self.currency_graph[base_bid] = { quote_ask: converted_ask }

        #
        # CONNECT SAME CURRENCY ASK TO BID
        #

        same_currency_weight = Decimal(1)

        try:
            self.currency_graph[quote_ask][quote_bid] = same_currency_weight
        except KeyError:
            self.currency_graph[quote_ask] = { quote_bid: same_currency_weight }

        try:
            self.currency_graph[base_ask][base_bid] = same_currency_weight
        except KeyError:
            self.currency_graph[base_ask] = { base_bid: same_currency_weight }

    def find_arbitrage_path(self, start, target):
        """
        Find the path that maximizes the spread between two currencies

        :param start: start currency
        :param target: target currency
        :returns: tuple(path, distance)
            - path: best path from start to target that maximizes price spread
            - distance: total value obtained from path
        """

        visited = dict.fromkeys(self.currency_graph.keys(), False)
        distance = dict.fromkeys(self.currency_graph.keys(), 0)
        parents = dict.fromkeys(self.currency_graph.keys(), -1)

        distance[start] = Decimal(1)
        node = start

        while not visited[node]:
            visited[node] = True
            edges = self.currency_graph[node]

            for next_node, weight in edges.items():
                path = self._get_path(start, node, parents)

                if not next_node in path:
                    new_distance = distance[node] / weight

                    if distance[next_node] < new_distance:
                        distance[next_node] = new_distance
                        parents[next_node] = node

            node = start
            dist = 0

            for i in self.currency_graph.keys():
                if not visited[i] and dist < distance[i]:
                    dist = distance[i]
                    node = i

        path = self._get_path(start, target, parents)

        return path, distance[target]

    def _get_path(self, start, target, parents):
        """
        Get currency path from a dict of parents

        :param start: start of the path
        :param target: end of the path
        :param parents: dict mapping nodes to parents
        :returns: list(currency)
            - currency: the next currency in the path
        """

        # Break out of infinite loops
        MAX_PATH_LENGTH = 16
        i = 0

        path = [target]
        p = target

        while p != start and p != -1 and i < MAX_PATH_LENGTH:
            p = parents[p]
            path.insert(0, p)
            i += 1

        return path

    @classmethod
    def get_bid(cls, currency):
        """
        Get the key for a currency bid node

        :param currency: the currency
        :returns: the key for the bid node
        """

        key = cls.INDEX_FORMAT.format(currency, cls.BID_KEY)
        return key

    @classmethod
    def get_ask(cls, currency):
        """
        Get the key for a currency ask node

        :param currency: the currency
        :returns: the key for the ask node
        """

        key = cls.INDEX_FORMAT.format(currency, cls.ASK_KEY)
        return key

    @classmethod
    def get_base(cls, currency_pair):
        """
        Get the base currency from a pair

        :param key: the currency pair
        :returns: the base currency
        """

        currency_pair = currency_pair.split('-')

        try:
            currency = currency_pair[0]
        except IndexError:
            currency = None

        return currency

    @classmethod
    def get_quote(cls, currency_pair):
        """
        Get the quote currency from a pair

        :param key: the currency pair
        :returns: the quote currency
        """

        currency_pair = currency_pair.split('-')

        try:
            currency = currency_pair[1]
        except IndexError:
            currency = None

        return currency

    @classmethod
    def get_currency(cls, key):
        """
        Get the currency from a node key

        :param key: the node key
        :returns: the currency
        """

        key = key.split('_')

        try:
            currency = key[0]
        except IndexError:
            currency = None

        return currency

    @classmethod
    def is_bid(cls, key):
        """
        Check if a node key belongs to a bid node

        :param key: the node key
        :returns: True or False
        """

        key = key.split('_')

        try:
            is_bid = key[1] == cls.BID_KEY
        except IndexError:
            is_bid = None

        return is_bid

    @classmethod
    def is_ask(cls, key):
        """
        Check if a node key belongs to a ask node

        :param key: the node key
        :returns: True or False
        """

        key = key.split('_')

        try:
            is_ask = key[1] == cls.ASK_KEY
        except IndexError:
            is_ask = None

        return is_ask

    def get_currency_pair(self, key1, key2):
        """
        Get the currency pair formed by two node keys

        `None` is returned if no valid currency pair can be formed with the
        two keys.

        :param key1: first node key
        :param key2: second node key
        :returns: tuple(base, quote)
            - base: the base currency
            - quote: the quote currency
        :rtype: tuple
        """

        currency1 = CurrencyGraph.get_currency(key1)
        currency2 = CurrencyGraph.get_currency(key2)

        for currency_pair in self.currency_pairs:
            base = currency_pair[CurrencyGraph.BASE_KEY]
            is_base = base in [currency1, currency2]

            quote = currency_pair[CurrencyGraph.QUOTE_KEY]
            is_quote = quote in [currency1, currency2]

            if is_base and is_quote:
                return currency_pair['base'], currency_pair['quote']

        return None, None

    def get_next_currency_pair(self, path):
        """
        Get the next currency pair in the path

        :param path: a path of currency nodes
        :returns: tuple(base, quote, current_node)
            - base: the base currency
            - quote: the quote currency
            - current_node: the current node used for the currency pair
        """

        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]

            if CurrencyGraph.is_bid(current_node):
                break

        base, quote = self.get_currency_pair(current_node, next_node)

        return base, quote, current_node

    def get_next_signal(self, path):
        """
        Get the next trade signal in the path

        The trade signal is either `CurrencyGraph.BUY_ORDER` or
        `CurrencyGraph.SELL_ORDER`.

        Method returns `False` if the next signal in the path is invalid.

        :param path: a path of currency nodes
        :returns: tuple(trade_signal, currency_pair)
            - trade_signal: either a buy or a sell signal
            - currency_pair: the currency pair that should be traded on
        """

        base, quote, current_node = self.get_next_currency_pair(path)

        currency = CurrencyGraph.get_currency(current_node)

        currency_pair = '{}-{}'.format(base, quote)

        if quote == currency:
            return CurrencyGraph.BUY_ORDER, currency_pair

        elif base == currency:
            return CurrencyGraph.SELL_ORDER, currency_pair

        else:
            return False
