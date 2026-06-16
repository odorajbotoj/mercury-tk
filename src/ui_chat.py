import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

import datetime, os, csv

import kiss


class MTkChat:
    def __init__(self, win, net, cs, v):
        self.net = net
        self.callsign = cs
        self.bw = "500"
        self.chatPath = "chat"
        self.VERSION = v

        self.sessionTime = ""  # 当前 connection 的建立时间
        self.sessionPath = ""  # 当前 connection 历史保存的路径

        self.draw_win(win)

    # UI
    def draw_win(self, win):
        # chat notebook
        chatNotebook = ttk.Notebook(win)
        chatNotebook.grid(row=2, column=0, sticky="nsew")

        # CQ and connection
        cqPage = ttk.Frame(chatNotebook)
        cqPage.grid_rowconfigure(0, weight=1)
        cqPage.grid_columnconfigure(0, weight=1)
        chatNotebook.add(cqPage, text="CQ and connection")
        self.cqText = tk.Text(cqPage, state="disabled", height=1, width=1)
        self.cqText.grid(row=0, column=0, columnspan=5, sticky="nsew")
        sbCq = ttk.Scrollbar(cqPage)
        sbCq.grid(row=0, column=5, sticky="ns")
        self.cqText.configure(yscrollcommand=sbCq.set)
        sbCq.configure(command=self.cqText.yview)
        self.connectDest = tk.StringVar(cqPage)
        dest = ttk.Entry(cqPage, textvariable=self.connectDest)
        dest.grid(row=1, column=0, sticky="ew")
        dest.bind("<Return>", lambda _: self.cb_connect_dest())
        ttk.Button(cqPage, text="Send CQ", command=self.cb_cq).grid(row=1, column=1)
        ttk.Button(cqPage, text="Connect...", command=self.cb_connect_dest).grid(
            row=1, column=2
        )
        ttk.Button(cqPage, text="Disconnect", command=self.cb_disconnect).grid(
            row=1, column=3
        )
        ttk.Button(cqPage, text="Abort", command=self.cb_abort).grid(row=1, column=4)

        # chat
        chatPage = ttk.Frame(chatNotebook)
        chatPage.grid_rowconfigure(0, weight=1)
        chatPage.grid_columnconfigure(0, weight=1)
        chatNotebook.add(chatPage, text="Chat")
        self.chatText = tk.Text(chatPage, state="disabled", height=1, width=1)
        self.chatText.grid(row=0, column=0, columnspan=3, sticky="nsew")
        sbChat = ttk.Scrollbar(chatPage)
        sbChat.grid(row=0, column=3, sticky="ns")
        self.chatText.configure(yscrollcommand=sbChat.set)
        sbChat.configure(command=self.chatText.yview)
        self.recvTmp = tk.StringVar(chatPage)
        ttk.Entry(chatPage, textvariable=self.recvTmp, state="disabled").grid(
            row=1, column=0, columnspan=3, sticky="ew"
        )
        self.chatTextInput = tk.StringVar(chatPage)
        inp = ttk.Entry(chatPage, textvariable=self.chatTextInput)
        inp.grid(row=2, column=0, sticky="ew")
        inp.bind("<Return>", lambda _: self.cb_send())
        ttk.Button(chatPage, text="Send", command=self.cb_send).grid(
            row=2, column=1, sticky="nsew"
        )
        ttk.Button(chatPage, text="Send file...", command=self.cb_send_file).grid(
            row=2, column=2, sticky="nsew"
        )

        # broadcast
        broadcastPage = ttk.Frame(chatNotebook)
        broadcastPage.grid_rowconfigure(0, weight=1)
        broadcastPage.grid_columnconfigure(0, weight=1)
        chatNotebook.add(broadcastPage, text="Broadcast")
        self.broadcast = tk.Text(broadcastPage, state="disabled", height=1, width=1)
        self.broadcast.grid(row=0, column=0, columnspan=2, sticky="nsew")
        sbBcast = ttk.Scrollbar(broadcastPage)
        sbBcast.grid(row=0, column=2, sticky="ns")
        self.broadcast.configure(yscrollcommand=sbBcast.set)
        sbBcast.configure(command=self.broadcast.yview)
        self.broadcastInput = tk.StringVar(broadcastPage)
        bcast = ttk.Entry(broadcastPage, textvariable=self.broadcastInput)
        bcast.grid(row=1, column=0, sticky="ew")
        bcast.bind("<Return>", lambda _: self.cb_broadcast())
        ttk.Button(broadcastPage, text="Broadcast", command=self.cb_broadcast).grid(
            row=1, column=1, sticky="nsew"
        )

        # command logs
        cmdlogPage = ttk.Frame(chatNotebook)
        cmdlogPage.grid_rowconfigure(0, weight=1)
        cmdlogPage.grid_columnconfigure(0, weight=1)
        chatNotebook.add(cmdlogPage, text="Command logs")
        self.cmdLog = tk.Text(cmdlogPage)
        self.cmdLog.insert(
            tk.END,
            f"mercury-tk by BG4QBF\nVersion: {self.VERSION}\nneed Mercury v1.9.9+\n\n",
        )
        self.cmdLog.see(tk.END)
        self.cmdLog.configure(state="disabled")
        self.cmdLog.grid(row=0, column=0, sticky="nsew")
        sbCmd = ttk.Scrollbar(cmdlogPage)
        sbCmd.grid(row=0, column=1, sticky="ns")
        self.cmdLog.configure(yscrollcommand=sbCmd.set)
        sbCmd.configure(command=self.cmdLog.yview)

    # CALLBACKS
    def cb_cq(self):
        if self.net.closed:
            return
        if self.callsign == "":
            messagebox.showerror("Error", "No callsign")
            return
        cmd = f"CQFRAME {self.callsign} {self.bw}"
        # 追加到命令历史
        self.net.dataQ.put({"dest": "cmd", "payload": cmd + "\r"})
        self.cmdLog.configure(state="normal")
        self.cmdLog.insert(
            tk.END,
            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: {cmd}\n",
        )
        self.cmdLog.configure(state="disabled")
        self.cmdLog.see(tk.END)
        # 追加到CQ历史
        self.cqText.configure(state="normal")
        self.cqText.insert(
            tk.END,
            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: {cmd}\n",
        )
        self.cqText.configure(state="disabled")
        self.cqText.see(tk.END)

    def cb_connect_dest(self):
        if self.net.closed:
            return
        if self.callsign == "":
            messagebox.showerror("Error", "No callsign")
            return
        if self.connectDest.get() == "":
            messagebox.showerror("Error", "No destination callsign")
            return
        cmd = f"CONNECT {self.callsign} {self.connectDest.get()}"
        self.net.dataQ.put({"dest": "cmd", "payload": cmd + "\r"})
        # 追加到命令历史
        self.cmdLog.configure(state="normal")
        self.cmdLog.insert(
            tk.END,
            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: {cmd}\n",
        )
        self.cmdLog.configure(state="disabled")
        self.cmdLog.see(tk.END)
        self.connectDest.set("")

    def cb_disconnect(self):
        if self.net.closed:
            return
        self.net.dataQ.put({"dest": "cmd", "payload": "DISCONNECT\r"})
        # 追加到命令历史
        self.cmdLog.configure(state="normal")
        self.cmdLog.insert(
            tk.END,
            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: DISCONNECT\n",
        )
        self.cmdLog.configure(state="disabled")
        self.cmdLog.see(tk.END)

    def cb_abort(self):
        if self.net.closed:
            return
        self.net.dataQ.put({"dest": "cmd", "payload": "ABORT\r"})
        # 追加到命令历史
        self.cmdLog.configure(state="normal")
        self.cmdLog.insert(
            tk.END,
            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: ABORT\n",
        )
        self.cmdLog.configure(state="disabled")
        self.cmdLog.see(tk.END)

    def cb_send(self):
        # 检查
        if self.net.closed:
            return
        if self.sessionTime == "":
            return
        l = len(self.chatTextInput.get().encode())
        if l == 0:
            return
        if l > 65535:
            messagebox.showerror("Error", "Too long", detail=f"{l} > max 65535")
            return
        # 入队
        self.net.dataQ.put(
            {
                "dest": "data",
                "payload": bytes([10, l // 256, l % 256, 13])
                + f"{self.chatTextInput.get()}\n".encode(),
            }
        )
        # 追加
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.chatText.configure(state="normal")
        self.chatText.insert(
            tk.END,
            f"{dt} send: {self.chatTextInput.get()}\n",
        )
        # 保存
        with open(
            os.path.join(self.sessionPath, "chat.csv"),
            "a",
            encoding="utf-8",
        ) as f:
            w = csv.writer(f)
            w.writerow([dt, "send", "chat", self.chatTextInput.get()])
        self.chatText.configure(state="disabled")
        self.chatText.see(tk.END)
        self.chatTextInput.set("")

    def cb_send_file(self):
        if self.net.closed:
            return
        if self.sessionTime == "":
            return
        f = filedialog.askopenfile("rb", title="File to send")
        if not f:
            return
        content = f.read()
        name = os.path.split(f.name)[1]
        f.close()
        l = len(content)
        if l > 65535:
            messagebox.showerror("Error", "Too large", detail=f"{l} > max 65535")
            return
        self.net.dataQ.put(
            {
                "dest": "data",
                "payload": f"\r{name}\r".encode()
                + bytes([l // 256, l % 256, 13])
                + content
                + "\r".encode(),
            }
        )
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.chatText.configure(state="normal")
        self.chatText.insert(
            tk.END,
            f"{dt} send file: {name}\n",
        )
        with open(
            os.path.join(self.sessionPath, "chat.csv"),
            "a",
            encoding="utf-8",
        ) as f:
            w = csv.writer(f)
            w.writerow([dt, "send", "file", name])
        self.chatText.configure(state="disabled")
        self.chatText.see(tk.END)

    def cb_broadcast(self):
        # 仅允许ASCII, 长度不超过126
        if self.net.closed:
            return
        s = self.broadcastInput.get()
        if s == "":
            return
        for i in s:
            if ord(i) > 127:
                messagebox.showerror("Error", "input ASCII only")
                return
        if len(s.encode()) > 126:
            messagebox.showerror(
                "Error",
                "Too long",
                detail=f"{len(s.encode())} > 126",
            )
            return
        self.net.dataQ.put(
            {
                "dest": "kiss",
                "payload": kiss.kiss_encode(s.encode(), kiss.CMD_DATA),
            }
        )
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.broadcast.configure(state="normal")
        self.broadcast.insert(tk.END, f"{dt} send: {s}\n")
        self.broadcast.configure(state="disabled")
        self.broadcast.see(tk.END)
        with open(
            os.path.join(self.chatPath, "broadcast.csv"),
            "a",
            encoding="utf-8",
        ) as f:
            w = csv.writer(f)
            w.writerow([dt, "send", self.broadcastInput.get()])
        self.broadcastInput.set("")

    # DATA
    def append_to_text(self, name, vals):
        target = None
        if name == "cq":
            target = self.cqText
        elif name == "chat":
            target = self.chatText
        elif name == "bcast":
            target = self.broadcast
        elif name == "cmd":
            target = self.cmdLog
        else:
            return
        target.configure(state="normal")
        for i in vals:
            target.insert(tk.END, i)
        target.configure(state="disabled")
        target.see(tk.END)

    def update_recv_tmp(self, v):
        self.recvTmp.set(v)

    def update_bandwidth(self, v):
        self.bw = v

    def update_chat_path(self, v):
        self.chatPath = v

    def clear_chat_text(self):
        self.chatText.configure(state="normal")
        self.chatText.delete("1.0", tk.END)
        self.chatText.configure(state="disabled")

    def set_mycallsign(self, cs):
        self.callsign = cs

    def get_session_time(self):
        return self.sessionTime

    def set_session_time(self, v):
        self.sessionTime = v

    def get_session_path(self):
        return self.sessionPath

    def set_session_path(self, v):
        self.sessionPath = v
