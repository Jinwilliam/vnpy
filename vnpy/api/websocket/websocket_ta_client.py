import json
import ssl
import sys
import traceback
import socket
from datetime import datetime
from threading import Lock, Thread
from time import sleep

import websocket


class WebsocketTAClient(object):

    def __init__(self):
        """Constructor"""
        self.host = None

        self._ws_lock = Lock()
        self._ws = None

        self._worker_thread = None
        self._ping_thread = None
        self._active = False

        self.proxy_host = None
        self.proxy_port = None
        self.ping_interval = 60     # seconds
        self.header = {}

        # For debugging
        self._last_sent_text = None
        self._last_received_text = None

    def init(self, host: str, proxy_host: str = "", proxy_port: int = 0, ping_interval: int = 60, header: dict = None):
        """
        :param ping_interval: unit: seconds, type: int
        """
        self.host = host
        self.ping_interval = ping_interval  # seconds

        if header:
            self.header = header

        if proxy_host and proxy_port:
            self.proxy_host = proxy_host
            self.proxy_port = proxy_port

    def start(self):
        """
        Start the client and on_connected function is called after webscoket
        is connected succesfully.

        Please don't send packet untill on_connected fucntion is called.
        """

        self._active = True
        self._worker_thread = Thread(target=self._run)
        self._worker_thread.setDaemon(True)

        self._ping_thread = Thread(target=self._run_ping)
        self._ping_thread.setDaemon(True)

        self._worker_thread.start()
        self._ping_thread.start()


    def stop(self):
        """
        Stop the client.
        """
        self._active = False
        self._disconnect()

    def join(self):
        """
        Wait till all threads finish.

        This function cannot be called from worker thread or callback function.
        """
        self._ping_thread.join()
        self._worker_thread.join()

    def send_packet(self, packet: dict):
        """
        Send a packet (dict data) to server

        override this if you want to send non-json packet
        """
        text = json.dumps(packet)
        self._record_last_sent_text(text)
        return self._send_text(text)

    def _send_text(self, text: str):
        """
        Send a text string to server.
        """
        ws = self._ws
        if ws:
            ws.send(text, opcode=websocket.ABNF.OPCODE_TEXT)

    def _send_binary(self, data: bytes):
        """
        Send bytes data to server.
        """
        ws = self._ws
        if ws:
            ws._send_binary(data)

    def _create_connection(self, *args, **kwargs):
        """"""
        return websocket.create_connection(*args, **kwargs)

    def _ensure_connection(self):
        """"""
        triggered = False
        with self._ws_lock:
            if self._ws is None:
                self._ws = self._create_connection(
                    self.host,
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    http_proxy_host=self.proxy_host,
                    http_proxy_port=self.proxy_port,
                    header=self.header
                )
                triggered = True
        if triggered:
            self.on_connected()

    def _disconnect(self):
        """
        """
        triggered = False
        with self._ws_lock:
            if self._ws:
                ws: websocket.WebSocket = self._ws
                self._ws = None

                triggered = True
        if triggered:
            ws.close()
            self.on_disconnected()

    def _run(self):
        """
        Keep running till stop is called.
        """
        try:
            while self._active:
                try:
                    self._ensure_connection()
                    ws = self._ws
                    if ws:
                        text = ws.recv()

                        # ws object is closed when recv function is blocking
                        if not text:
                            self._disconnect()
                            continue

                        self._record_last_received_text(text)

                        try:
                            data, dtype = self.unpack_data(text)
                        except ValueError as e:
                            print("websocket unable to parse data: " + text)
                            raise e

                        self.on_packet(data, dtype)
                # ws is closed before recv function is called
                # For socket.error, see Issue #1608
                except (websocket.WebSocketConnectionClosedException, socket.error):
                    self._disconnect()

                # other internal exception raised in on_packet
                except:  # noqa
                    et, ev, tb = sys.exc_info()
                    self.on_error(et, ev, tb)
                    self._disconnect()
        except:  # noqa
            et, ev, tb = sys.exc_info()
            self.on_error(et, ev, tb)
        self._disconnect()

    @staticmethod
    def unpack_data(data: str):
        """
        Default serialization format is json.

        override this method if you want to use other serialization format.
        """
        dtype = 'str'
        if data.startswith('{') and data.endswith('}'):
            dtype = 'json'
            return json.loads(data), dtype
        return data, dtype

    def _run_ping(self):
        """"""
        while self._active:
            try:
                self._ping()
            except:  # noqa
                et, ev, tb = sys.exc_info()
                self.on_error(et, ev, tb)

                # self._run() will reconnect websocket
                sleep(1)

            for i in range(self.ping_interval):
                if not self._active:
                    break
                sleep(1)

    def _ping(self):
        """"""
        ws = self._ws
        if ws:
            ws.send("ping", websocket.ABNF.OPCODE_PING)

    @staticmethod
    def on_connected():
        """
        Callback when websocket is connected successfully.
        """
        pass

    @staticmethod
    def on_disconnected():
        """
        Callback when websocket connection is lost.
        """
        pass

    @staticmethod
    def on_packet(packet: dict, dtype: str):
        """
        Callback when receiving data from server.
        """
        pass

    def on_error(self, exception_type: type, exception_value: Exception, tb):
        """
        Callback when exception raised.
        """
        sys.stderr.write(
            self.exception_detail(exception_type, exception_value, tb)
        )
        return sys.excepthook(exception_type, exception_value, tb)

    def exception_detail(
        self, exception_type: type, exception_value: Exception, tb
    ):
        """
        Print detailed exception information.
        """
        text = "[{}]: Unhandled WebSocket Error:{}\n".format(
            datetime.now().isoformat(), exception_type
        )
        text += "LastSentText:\n{}\n".format(self._last_sent_text)
        text += "LastReceivedText:\n{}\n".format(self._last_received_text)
        text += "Exception trace: \n"
        text += "".join(
            traceback.format_exception(exception_type, exception_value, tb)
        )
        return text

    def _record_last_sent_text(self, text: str):
        """
        Record last sent text for debug purpose.
        """
        self._last_sent_text = text[:1000]

    def _record_last_received_text(self, text: str):
        """
        Record last received text for debug purpose.
        """
        self._last_received_text = text[:1000]
    def keep_user_stream(self):
        return 1

if __name__ == '__main__':
    wsta = WebsocketTAClient()
    wsta.init("ws://127.0.0.1:9443")
    wsta.start()
    while True:
        sleep(1)
        wsta.send_packet({'msg':'test'})
