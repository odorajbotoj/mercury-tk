import queue
import threading
import socket
import websocket
import urllib.parse
import json


class MtkNet:
    def __init__(self):
        self.cmdConn = None
        self.dataConn = None
        self.kissConn = None
        self.wsConn = None
        self.closed = True
        self.uiQ = queue.Queue()
        self.dataQ = queue.Queue()

    def connect(self, tcpport, kissport, wsport):
        if not self.closed:
            return
        self.closed = False
        # tcp
        tcpUrl = urllib.parse.urlparse("tcp://" + tcpport)
        self.cmdConn = socket.socket(
            socket.getaddrinfo(tcpUrl.hostname, tcpUrl.port)[0][0], socket.SOCK_STREAM
        )
        try:
            self.cmdConn.connect((tcpUrl.hostname, tcpUrl.port))
        except:
            self.disconnect()
            return
        self.dataConn = socket.socket(
            socket.getaddrinfo(tcpUrl.hostname, tcpUrl.port)[0][0], socket.SOCK_STREAM
        )
        try:
            self.dataConn.connect((tcpUrl.hostname, tcpUrl.port + 1))
        except:
            self.disconnect()
            return
        # kiss
        kissUrl = urllib.parse.urlparse("tcp://" + kissport)
        self.kissConn = socket.socket(
            socket.getaddrinfo(kissUrl.hostname, kissUrl.port)[0][0], socket.SOCK_STREAM
        )
        try:
            self.kissConn.connect((kissUrl.hostname, kissUrl.port))
        except:
            self.disconnect()
            return
        # ws
        self.wsConn = websocket.WebSocketApp(
            wsport, on_message=self.ws_on_message, on_close=self.ws_on_close
        )
        while not self.dataQ.empty():
            self.dataQ.get()  # clear
        threading.Thread(target=self.ws_run, daemon=True).start()
        threading.Thread(target=self.handle_data, daemon=True).start()
        threading.Thread(target=self.cmd_recv, daemon=True).start()
        threading.Thread(target=self.data_recv, daemon=True).start()
        threading.Thread(target=self.kiss_recv, daemon=True).start()
        self.uiQ.put({"type": "modem", "connected": True})

    def disconnect(self):
        if self.closed:
            return
        else:
            self.closed = True
        if type(self.cmdConn) == socket.socket:
            try:
                self.cmdConn.close()
            except:
                pass
        if type(self.dataConn) == socket.socket:
            try:
                self.dataConn.close()
            except:
                pass
        if type(self.kissConn) == socket.socket:
            try:
                self.kissConn.close()
            except:
                pass
        if type(self.wsConn) == websocket.WebSocketApp:
            try:
                self.wsConn.close()
            except:
                pass
        self.uiQ.put({"type": "modem", "connected": False})

    def ws_on_message(self, _, msg):
        if type(msg) == str:
            self.uiQ.put({"type": "ws", "payload": json.loads(msg)})
        elif type(msg) == bytes:
            self.uiQ.put({"type": "waterfall", "payload": msg})

    def ws_on_close(self, ws, stat, msg):
        _ = ws, stat, msg
        self.disconnect()

    def ws_run(self):
        if type(self.wsConn) == websocket.WebSocketApp:
            self.wsConn.run_forever()

    def cmd_recv(self):
        buf = ""
        while True:
            if self.closed:
                return
            if not self.cmdConn:
                return
            try:
                buf += self.cmdConn.recv(1024).decode()
                l = buf.split("\r", 1)
                while len(l) == 2:
                    self.uiQ.put({"type": "cmd", "payload": l[0]})
                    buf = l[1]
                    l = l[1].split("\r", 1)
            except:
                return

    def data_recv(self):
        while True:
            if self.closed:
                return
            if not self.dataConn:
                return
            try:
                self.uiQ.put({"type": "data", "payload": self.dataConn.recv(2048)})
            except:
                return

    def kiss_recv(self):
        while True:
            if self.closed:
                return
            if not self.kissConn:
                return
            try:
                self.uiQ.put({"type": "kiss", "payload": self.kissConn.recv(1024)})
            except:
                return

    def handle_data(self):
        while True:
            data = self.dataQ.get()
            if self.closed:
                return
            if data["dest"] == "ws":
                if self.wsConn:
                    self.wsConn.send_text(json.dumps(data["payload"]))
            elif data["dest"] == "cmd":
                if self.cmdConn:
                    self.cmdConn.sendall(data["payload"].encode())
            elif data["dest"] == "data":
                if self.dataConn:
                    self.dataConn.sendall(data["payload"])
            elif data["dest"] == "kiss":
                if self.kissConn:
                    self.kissConn.sendall(data["payload"])
