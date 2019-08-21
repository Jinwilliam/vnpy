"""
Gateway for TradeAgent Crypto Exchange.
"""

import urllib
import hashlib
import hmac
import time
from copy import copy
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock

from vnpy.api.websocket import WebsocketTAClient
from vnpy.trader.constant import (
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    ContractData,
    BarData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest
)
from vnpy.trader.event import EVENT_TIMER
from vnpy.event import Event


REST_HOST = "https://www.TradeAgent.com"
WEBSOCKET_TRADE_HOST = "ws://127.0.0.1:9443/ws/"

STATUS_TradeAgent2VT = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "REJECTED": Status.REJECTED
}

ORDERTYPE_VT2TradeAgent = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET"
}
ORDERTYPE_TradeAgent2VT = {v: k for k, v in ORDERTYPE_VT2TradeAgent.items()}

DIRECTION_VT2TradeAgent = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_TradeAgent2VT = {v: k for k, v in DIRECTION_VT2TradeAgent.items()}

INTERVAL_VT2TradeAgent = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}


class Security(Enum):
    NONE = 0
    SIGNED = 1
    API_KEY = 2


symbol_name_map = {}


class TradeAgentGateway(BaseGateway):
    """
    VN Trader Gateway for TradeAgent connection.
    """

    default_setting = {
        "server_host": "ws://127.0.0.1:9443",
        "account_id": "",
    }

    exchanges = [Exchange.SSE, Exchange.SZSE]

    def __init__(self, event_engine):
        """Constructor"""
        super().__init__(event_engine, "TradeAgent")

        self.trade_ws_api = TradeAgentTradeWebsocketApi(self)

        self.event_engine.register(EVENT_TIMER, self.process_timer_event)

    def connect(self, setting: dict):
        """"""
        server = setting["server_host"]
        account_id = setting["account_id"]
        self.trade_ws_api.init(server)
        self.trade_ws_api.start()
        self.trade_ws_api.send_packet({'msg':'test'})

    def subscribe(self, req: SubscribeRequest):
        """"""
        pass

    def send_order(self, req: OrderRequest):
        """"""
        return self.trade_ws_api.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.trade_ws_api.cancel_order(req)

    def query_account(self):
        """"""
        pass

    def query_position(self):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        return self.trade_ws_api.query_history(req)

    def close(self):
        """"""
        self.trade_ws_api.stop()

    def process_timer_event(self, event: Event):
        """"""
        self.trade_ws_api.keep_user_stream()


class TradeAgentTradeWebsocketApi(WebsocketTAClient):
    """"""

    def __init__(self, gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

    def connect(self, url, proxy_host=None, proxy_port=None):
        """"""
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self):
        """"""
        self.gateway.write_log("交易Websocket API连接成功")

    def on_packet(self, packet: dict, dtype: str):  # type: (dict)->None
        """"""
        if dtype == 'str':
            self.gateway.write_log(packet)
        else:
            self.gateway.write_log(packet)

    def on_account(self, packet):
        """"""
        for d in packet["B"]:
            account = AccountData(
                accountid=d["a"],
                balance=float(d["f"]) + float(d["l"]),
                frozen=float(d["l"]),
                gateway_name=self.gateway_name
            )
            
            if account.balance:
                self.gateway.on_account(account)

    def on_order(self, packet: dict):
        """"""
        dt = datetime.fromtimestamp(packet["O"] / 1000)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")

        if packet["C"] == "null":
            orderid = packet["c"]
        else:
            orderid = packet["C"]

        order = OrderData(
            symbol=packet["s"],
            exchange=Exchange.TradeAgent,
            orderid=orderid,
            type=ORDERTYPE_TradeAgent2VT[packet["o"]],
            direction=DIRECTION_TradeAgent2VT[packet["S"]],
            price=float(packet["p"]),
            volume=float(packet["q"]),
            traded=float(packet["z"]),
            status=STATUS_TradeAgent2VT[packet["X"]],
            time=time,
            gateway_name=self.gateway_name
        )

        self.gateway.on_order(order)

        # Push trade event
        trade_volume = float(packet["l"])
        if not trade_volume:
            return

        trade_dt = datetime.fromtimestamp(packet["T"] / 1000)
        trade_time = trade_dt.strftime("%Y-%m-%d %H:%M:%S")

        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=packet["t"],
            direction=order.direction,
            price=float(packet["L"]),
            volume=trade_volume,
            time=trade_time,
            gateway_name=self.gateway_name,
        )
        self.gateway.on_trade(trade)
        
    def send_order(self, req):
        """
		req = OrderRequest(
            symbol=symbol,
            exchange=Exchange(str(self.exchange_combo.currentText())),
            direction=Direction(str(self.direction_combo.currentText())),
            type=OrderType(str(self.order_type_combo.currentText())),
            volume=volume,
            price=price,
            offset=Offset(str(self.offset_combo.currentText())),
        )
        """
        self.gateway.write_log("Send Order.")
        self.send_packet({'data': req.symbol})
        
    def cancel_order(self, req):
        pass
    
    def query_history(self, req):
        pass