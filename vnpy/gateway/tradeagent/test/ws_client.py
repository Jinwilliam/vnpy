import json
import ssl
import sys
import pdb
import traceback
from datetime import datetime
from threading import Thread
from time import sleep
import socket
import signal

import websocket

class WebsocketClient(object):
    def __init__(self, host, header={}):
        """Constructor"""
        self.host = host
        self.header = header
        self._worker_thread = None
        self._ws = None

        # For debugging
        self._last_sent_text = None
        self._last_received_text = None
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)

    def exit(self, signum, frame):
        print('Exit.')
        self._active = False
        sys.exit(0)

    def connect(self):
        triggered = False
        self._active = True
        if self._ws is None:
            try:
                self._ws = websocket.create_connection(self.host)
                triggered = True
            except Exception as e:
                print(e)

        if triggered:
            self.on_connected()
            self._worker_thread = Thread(target=self._run)
            self._worker_thread.setDaemon(True)
            self._worker_thread.start()

        return triggered

    def stop(self):
        """
        Stop the client.
        """
        self._active = False
        self._disconnect()

    def send_packet(self, packet):
        text = json.dumps(packet)
        self._record_last_sent_text(text)
        return self._send_text(text)

    def _send_text(self, text):
        """
        Send a text string to server.
        """
        ws = self._ws
        if ws:
            ws.send(text, opcode=websocket.ABNF.OPCODE_TEXT)

    def _send_binary(self, data):
        ws = self._ws
        if ws:
            ws._send_binary(data)

    def _disconnect(self):
        triggered = False
        if self._ws:
            ws = self._ws
            self._ws = None
            triggered = True
        if triggered:
            ws.close()
            self.on_disconnected()

    @staticmethod
    def unpack_data(data):
        if data.startswith('{') and data.endswith('}'):
            return json.loads(data)
        return data

    @staticmethod
    def on_connected():
        print("Connected.")

    @staticmethod
    def on_disconnected():
        print("DisConnected.")

    @staticmethod
    def on_packet(packet):
        print(packet)

    def on_error(self, exception_type, exception_value, tb):
        sys.stderr.write(
            self.exception_detail(exception_type, exception_value, tb)
        )
        return sys.excepthook(exception_type, exception_value, tb)

    def exception_detail(
        self, exception_type, exception_value, tb
    ):
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

    def _record_last_sent_text(self, text):
        """
        Record last sent text for debug purpose.
        """
        self._last_sent_text = text[:1000]

    def _record_last_received_text(self, text):
        """
        Record last received text for debug purpose.
        """
        self._last_received_text = text[:1000]

    def _run(self):
        """
        Keep running till stop is called.
        """
        try:
            while self._active:
                try:
                    ws = self._ws
                    if ws:
                        text = ws.recv()

                        # ws object is closed when recv function is blocking
                        if not text:
                            self._disconnect()
                            continue

                        self._record_last_received_text(text)

                        try:
                            data = self.unpack_data(text)
                        except ValueError as e:
                            print("websocket unable to parse data: " + text)
                            raise e

                        self.on_packet(data)
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

if __name__ == '__main__':
    debug = False
    ws = WebsocketClient(host="ws://127.0.0.1:9443/")
    if ws.connect():
        ws.send_packet({'msg': 'test'})
        if debug:
            print("socket object: ws, try using ws.send_packet(json) to communicat.")
            pdb.set_trace()

        while True:
            sleep(1)
