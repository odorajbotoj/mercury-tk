import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox

import serial.tools.list_ports as serial_list_ports

import datetime, os, csv

# user-define
import adif
import mtk_net
import kiss
import waterfall


class MercuryTk:  # 主 ui 绘制
    def __init__(self):
        self.net = mtk_net.MtkNet()
        self.audioCaptureDevices = {}  # 存放音频输入设备的 name - id 对应
        self.audioPlaybackDevices = {}  # 存放音频输出设备的 name - id 对应
        self.radioModels = {}  # 存放 hamlib 设备类型的 name - id 对应
        self.recvStat = 0  # 0 Idle, 1 Len, 2 Str, 3 Name, 4 Size, 5 File
        self.recvTime = datetime.datetime.now()  # 接收到数据的时间
        self.fileNameTmp = b""  # 接收到的文件名 (缓冲区)
        self.lenSaved = 0  # 接收数据长度的状态
        self.contentLenTmp = 0  # 接收数据长度 (缓冲区)
        self.dataTmp = b""  # 接收数据缓冲区
        self.sessionTime = ""  # 当前 connection 的建立时间
        self.sessionPath = ""  # 当前 connection 历史保存的路径

        # 主窗口
        self.window = tk.Tk()
        self.window.title("mercury-tk")
        self.window.geometry("1024x768+10+10")
        self.window.grid_rowconfigure(2, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self.win_add_settings()
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=1, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        self.win_add_chat()
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=3, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        self.win_add_status()
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=5, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        # waterfall
        self.wfCanvas = tk.Canvas(self.window, bg="black", height=200)
        self.wfCanvas.grid(row=6, column=0, sticky="ew")
        self.wf = waterfall.Waterfall(self.wfCanvas)

        # 创建历史保存文件夹
        if not os.path.exists(self.chatPath.get()):
            os.makedirs(self.chatPath.get())

    # 以下为窗口各部分绘制流程, 太长了, 分割成几个函数

    def win_add_settings(self):
        # settings notebook
        settingsNotebook = ttk.Notebook(self.window)
        settingsNotebook.grid(row=0, column=0, sticky="ew")

        # mercury settings
        mercurySettings = ttk.Frame(settingsNotebook)
        mercurySettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(mercurySettings, text="Mercury")
        # base port
        ttk.Label(mercurySettings, text="Base port").grid(row=0, column=0)
        self.basePort = tk.StringVar(mercurySettings, "127.0.0.1:8300")
        ttk.Entry(mercurySettings, textvariable=self.basePort).grid(
            row=0, column=1, sticky="ew"
        )
        # kiss port
        ttk.Label(mercurySettings, text="KISS port").grid(row=1, column=0)
        self.kissPort = tk.StringVar(mercurySettings, "127.0.0.1:8100")
        ttk.Entry(mercurySettings, textvariable=self.kissPort).grid(
            row=1, column=1, sticky="ew"
        )
        # ws port
        ttk.Label(mercurySettings, text="Websocket port").grid(row=2, column=0)
        self.wsPort = tk.StringVar(mercurySettings, "ws://127.0.0.1:10000/websocket")
        ttk.Entry(mercurySettings, textvariable=self.wsPort).grid(
            row=2, column=1, sticky="ew"
        )
        # connect button
        self.connBtnText = tk.StringVar(mercurySettings, "Connect")
        ttk.Button(
            mercurySettings, textvariable=self.connBtnText, command=self.cb_connect
        ).grid(row=0, column=2, rowspan=3, sticky="ns")

        # hamlib settings
        hamlibSettings = ttk.Frame(settingsNotebook)
        hamlibSettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(hamlibSettings, text="Hamlib")
        # model
        ttk.Label(hamlibSettings, text="Model").grid(row=0, column=0)
        self.mdlCom = ttk.Combobox(hamlibSettings, state="readonly")
        self.mdlCom.grid(row=0, column=1, sticky="ew")
        # device
        ttk.Label(hamlibSettings, text="Device").grid(row=1, column=0)
        self.radioDevice = tk.StringVar(hamlibSettings)
        self.dvcCom = ttk.Combobox(hamlibSettings, textvariable=self.radioDevice)
        self.dvcCom.bind("<Button-1>", self.update_serial_port)
        self.dvcCom.bind("<FocusIn>", self.update_serial_port)
        self.dvcCom.grid(row=1, column=1, sticky="ew")
        # baudrate
        ttk.Label(hamlibSettings, text="Baudrate").grid(row=2, column=0)
        self.bdrtCom = ttk.Combobox(
            hamlibSettings,
            values=["0", "4800", "9600", "19200", "38400", "115200"],
            state="readonly",
        )
        self.bdrtCom.current(0)
        self.bdrtCom.grid(row=2, column=1, sticky="ew")
        # apply button
        ttk.Button(hamlibSettings, text="Apply", command=self.cb_apply_radio).grid(
            row=0, column=2, rowspan=3, sticky="ns"
        )

        # audio settings
        audioSettings = ttk.Frame(settingsNotebook)
        audioSettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(audioSettings, text="Audio")
        # capture
        ttk.Label(audioSettings, text="Capture device").grid(row=0, column=0)
        self.cptCom = ttk.Combobox(audioSettings)
        self.cptCom.grid(row=0, column=1, sticky="ew")
        # playback
        ttk.Label(audioSettings, text="Playback device").grid(row=1, column=0)
        self.plbkCom = ttk.Combobox(audioSettings)
        self.plbkCom.grid(row=1, column=1, sticky="ew")
        # channel
        ttk.Label(audioSettings, text="Capture input channel").grid(row=2, column=0)
        self.chnCom = ttk.Combobox(audioSettings)
        self.chnCom.grid(row=2, column=1, sticky="ew")
        # apply button
        ttk.Button(audioSettings, text="Apply", command=self.cb_apply_audio).grid(
            row=0, column=2, rowspan=3, sticky="ns"
        )

        # mycall settings
        mycallSettings = ttk.Frame(settingsNotebook)
        mycallSettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(mycallSettings, text="MyCall")
        # callsign
        ttk.Label(mycallSettings, text="Callsign").grid(row=0, column=0)
        self.myCallsign = tk.StringVar(mycallSettings)
        ttk.Entry(mycallSettings, textvariable=self.myCallsign).grid(
            row=0, column=1, sticky="ew"
        )
        self.secondaryCalls = []
        for i in range(4):
            ttk.Label(mycallSettings, text=f"Secondary callsign {i+1}").grid(
                row=i + 1, column=0
            )
            self.secondaryCalls.append(tk.StringVar(mycallSettings))
            ttk.Entry(mycallSettings, textvariable=self.secondaryCalls[i]).grid(
                row=i + 1, column=1, sticky="ew"
            )
        # bandwidth
        ttk.Label(mycallSettings, text="Bandwidth").grid(row=5, column=0)
        self.bwCom = ttk.Combobox(
            mycallSettings,
            values=["500", "2300"],
            state="readonly",
        )
        self.bwCom.current(0)
        self.bwCom.grid(row=5, column=1, sticky="ew")
        # apply button
        ttk.Button(mycallSettings, text="Apply", command=self.cb_set_call).grid(
            row=0, column=2, rowspan=6, sticky="ns"
        )

        # history settings
        historySettings = ttk.Frame(settingsNotebook)
        historySettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(historySettings, text="History")
        ttk.Label(historySettings, text="Save chat in path").grid(row=0, column=0)
        self.chatPath = tk.StringVar(historySettings, "chat")
        ttk.Entry(historySettings, textvariable=self.chatPath).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Button(
            historySettings, text="Browse...", command=self.browse_chat_path
        ).grid(row=0, column=2)

        # log settings
        logSettings = ttk.Frame(settingsNotebook)
        logSettings.grid_columnconfigure(1, weight=1)
        settingsNotebook.add(logSettings, text="Log")
        ttk.Label(logSettings, text="Save log to ADIF").grid(row=0, column=0)
        self.adifPath = tk.StringVar(logSettings, "mercury-tk.adi")
        ttk.Entry(logSettings, textvariable=self.adifPath).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Button(logSettings, text="Browse...", command=self.browse_adif).grid(
            row=0, column=2
        )
        # log to file
        ttk.Label(logSettings, text="Callsign").grid(row=1, column=0)  # callsign
        self.logDestCall = tk.StringVar(logSettings)
        ttk.Entry(logSettings, textvariable=self.logDestCall).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(logSettings, text="UTC Date").grid(row=2, column=0)  # date
        self.logDate = tk.StringVar(logSettings)
        dateEntry = ttk.Entry(logSettings, textvariable=self.logDate)
        dateEntry.grid(row=2, column=1, sticky="ew")
        dateEntry.bind("<Button-1>", self.update_log_date)
        dateEntry.bind("<FocusIn>", self.update_log_date)
        ttk.Label(logSettings, text="UTC Time").grid(row=3, column=0)  # time
        self.logTime = tk.StringVar(logSettings)
        timeEntry = ttk.Entry(logSettings, textvariable=self.logTime)
        timeEntry.grid(row=3, column=1, sticky="ew")
        timeEntry.bind("<Button-1>", self.update_log_time)
        timeEntry.bind("<FocusIn>", self.update_log_time)
        ttk.Label(logSettings, text="Freq (MHz)").grid(row=4, column=0)  # freq
        self.logFreq = tk.DoubleVar(logSettings)
        ttk.Entry(logSettings, textvariable=self.logFreq).grid(
            row=4, column=1, sticky="ew"
        )
        ttk.Label(logSettings, text="RxFreq (MHz)").grid(row=5, column=0)  # rxfreq
        self.logRxFreq = tk.DoubleVar(logSettings)
        ttk.Entry(logSettings, textvariable=self.logRxFreq).grid(
            row=5, column=1, sticky="ew"
        )
        ttk.Button(
            logSettings,
            text="Add log",
            command=lambda: adif.log_to_adif(
                self.adifPath.get(),
                self.logDestCall.get(),
                self.logDate.get(),
                self.logTime.get(),
                self.logFreq.get(),
                self.logRxFreq.get(),
            ),
        ).grid(row=1, column=2, rowspan=5, sticky="ns")

        # settings notebook end

    def win_add_chat(self):
        # chat notebook
        chatNotebook = ttk.Notebook(self.window)
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
        ttk.Entry(cqPage, textvariable=self.connectDest).grid(
            row=1, column=0, sticky="ew"
        )
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
        ttk.Entry(chatPage, textvariable=self.chatTextInput).grid(
            row=2, column=0, sticky="ew"
        )
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
        ttk.Entry(broadcastPage, textvariable=self.broadcastInput).grid(
            row=1, column=0, sticky="ew"
        )
        ttk.Button(broadcastPage, text="Broadcast", command=self.cb_broadcast).grid(
            row=1, column=1, sticky="nsew"
        )

        # command logs
        cmdlogPage = ttk.Frame(chatNotebook)
        cmdlogPage.grid_rowconfigure(0, weight=1)
        cmdlogPage.grid_columnconfigure(0, weight=1)
        chatNotebook.add(cmdlogPage, text="Command logs")
        self.cmdLog = tk.Text(cmdlogPage, state="disabled")
        self.cmdLog.grid(row=0, column=0, sticky="nsew")
        sbCmd = ttk.Scrollbar(cmdlogPage)
        sbCmd.grid(row=0, column=1, sticky="ns")
        self.cmdLog.configure(yscrollcommand=sbCmd.set)
        sbCmd.configure(command=self.cmdLog.yview)

        # chat notebook end

    def win_add_status(self):
        # status
        statusFrame = ttk.Frame(self.window)
        statusFrame.grid(row=4, column=0, sticky="ew")
        statusFrame.grid_columnconfigure(0, weight=1)
        statusFrame.grid_columnconfigure(1, weight=1)
        statusFrame.grid_columnconfigure(2, weight=1)

        # link status
        self.connStat = ttk.Label(
            statusFrame, text="MODEM DISCONNECTED", foreground="red"
        )
        self.connStat.grid(row=0, column=0)
        self.userCall = ttk.Label(statusFrame, text="UserCall ")
        self.userCall.grid(row=1, column=0)
        self.destCall = ttk.Label(statusFrame, text="DestCall ")
        self.destCall.grid(row=2, column=0)
        # bit status
        self.bitrate = ttk.Label(statusFrame, text="BR 0")
        self.bitrate.grid(row=0, column=1)
        self.bytesTx = ttk.Label(statusFrame, text="TX 0")
        self.bytesTx.grid(row=1, column=1)
        self.bytesRx = ttk.Label(statusFrame, text="RX 0")
        self.bytesRx.grid(row=2, column=1)
        # signal
        self.snr = ttk.Label(statusFrame, text="SNR 0.0")
        self.snr.grid(row=0, column=2)
        self.sync = ttk.Label(statusFrame, text="NO SYNC", foreground="red")
        self.sync.grid(row=1, column=2)
        self.direction = ttk.Label(statusFrame, text="DIR: RX", foreground="green")
        self.direction.grid(row=2, column=2)

        # status end

    # 以下为更新串口的回调

    def update_serial_port(self, _):
        l = []
        for i in serial_list_ports.comports():
            l.append(i.device)
        self.dvcCom["value"] = l
        self.dvcCom.current(0)

    # 以下为浏览路径的回调

    def browse_chat_path(self):
        self.chatPath.set(
            filedialog.askdirectory(
                initialdir=self.chatPath.get(), title="Select directory to save chat..."
            )
        )
        if not os.path.exists(self.chatPath.get()):
            os.makedirs(self.chatPath.get())

    def browse_adif(self):
        self.adifPath.set(
            filedialog.asksaveasfilename(
                initialfile=self.adifPath.get(), title="Select ADIF file to save log..."
            )
        )

    # 以下为更新时间的回调

    def update_log_date(self, _):
        self.logDate.set(
            datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        )

    def update_log_time(self, _):
        self.logTime.set(
            datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%SZ")
        )

    # 以下为按钮回调

    def cb_connect(self):
        if self.net.closed:
            self.net.connect(
                self.basePort.get(), self.kissPort.get(), self.wsPort.get()
            )
        else:
            self.net.disconnect()

    def cb_apply_radio(self):
        if self.net.closed:
            return
        self.net.dataQ.put(
            {
                "dest": "ws",
                "payload": {
                    "command": "set_radio_config",
                    "value": self.radioModels[self.mdlCom.get()],
                    "value2": self.radioDevice.get(),
                    "value3": self.bdrtCom.get(),
                },
            }
        )

    def cb_apply_audio(self):
        if self.net.closed:
            return
        self.net.dataQ.put(
            {
                "dest": "ws",
                "payload": {
                    "command": "set_audio_config",
                    "value": self.audioCaptureDevices[self.cptCom.get()],
                    "value2": self.audioPlaybackDevices[self.plbkCom.get()],
                    "value3": self.chnCom.get(),
                },
            }
        )

    def cb_set_call(self):
        if self.net.closed:
            return
        cmds = [
            f"MYCALL {self.myCallsign.get()} {self.secondaryCalls[0].get()} {self.secondaryCalls[1].get()} {self.secondaryCalls[2].get()} {self.secondaryCalls[3].get()}",
            f"BW{self.bwCom.get()}",
            "LISTEN ON",
        ]
        self.net.dataQ.put(
            {
                "dest": "cmd",
                "payload": "\r".join(cmds) + "\r",
            }
        )
        # 追加到命令历史
        self.cmdLog.configure(state="normal")
        for i in cmds:
            self.cmdLog.insert(
                tk.END,
                f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} send: {i}\n",
            )
        self.cmdLog.configure(state="disabled")
        self.cmdLog.see(tk.END)

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

    def cb_cq(self):
        if self.net.closed:
            return
        if self.myCallsign.get() == "":
            messagebox.showerror("Error", "No callsign")
            return
        cmd = f"CQFRAME {self.myCallsign.get()} {self.bwCom.get()}"
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
        if self.myCallsign.get() == "":
            messagebox.showerror("Error", "No callsign")
            return
        if self.connectDest.get() == "":
            messagebox.showerror("Error", "No destination callsign")
            return
        cmd = f"CONNECT {self.myCallsign.get()} {self.connectDest.get()}"
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

    def cb_send(self):
        # 检查
        if self.net.closed:
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
            os.path.join(self.chatPath.get(), "broadcast.csv"), "a", encoding="utf-8"
        ) as f:
            w = csv.writer(f)
            w.writerow([dt, "send", self.broadcastInput.get()])
        self.broadcastInput.set("")

    # 主App运行
    def run(self):
        self.handle_data()
        self.window.mainloop()

    # 处理数据
    def handle_data(self):
        while not self.net.uiQ.empty():
            data = self.net.uiQ.get()
            if data["type"] == "modem":  # 更新连接状态
                if data["connected"]:
                    self.connBtnText.set("Disconnect")
                    self.connStat.configure(text="MODEM CONNECTED", foreground="green")
                else:
                    self.connBtnText.set("Connect")
                    self.connStat.configure(text="MODEM DISCONNECTED", foreground="red")
                    messagebox.showerror(title="Error", message="Modem disconnected")
            elif data["type"] == "ws":  # 交给ws处理器
                self.handle_ws_data(data["payload"])
            elif data["type"] == "waterfall":  # 交给瀑布图处理器
                re = waterfall.parse_spectrum(data["payload"])
                if re:
                    self.wf.push(*re)
            elif data["type"] == "cmd":  # 追加到命令历史框, 两个特殊命令做额外处理
                self.cmdLog.configure(state="normal")
                self.cmdLog.insert(
                    tk.END,
                    f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} recv: {data["payload"]}\n",
                )
                self.cmdLog.configure(state="disabled")
                self.cmdLog.see(tk.END)
                if data["payload"].startswith("CQFRAME"):
                    self.cqText.configure(state="normal")
                    self.cqText.insert(
                        tk.END,
                        f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} recv: {data["payload"]}\n",
                    )
                    self.cqText.configure(state="disabled")
                    self.cqText.see(tk.END)
                elif data["payload"].startswith("BUFFER"):
                    self.recvTmp.set(f"Data remaining: {data["payload"][7:]}")
            elif data["type"] == "data":  # 交给数据处理器
                self.parse_data_payload(data["payload"])
            elif data["type"] == "kiss":  # 处理广播包
                l = kiss.kiss_decode(data["payload"])
                dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.broadcast.configure(state="normal")
                for pld in l:
                    self.broadcast.insert(
                        tk.END, f"{dt} recv: {pld.decode(errors="backslashreplace")}\n"
                    )
                self.broadcast.configure(state="disabled")
                self.broadcast.see(tk.END)
                with open(
                    os.path.join(self.chatPath.get(), "broadcast.csv"),
                    "a",
                    encoding="utf-8",
                ) as f:
                    for pld in l:
                        w = csv.writer(f)
                        w.writerow([dt, "recv", pld.decode(errors="backslashreplace")])
        self.window.after(50, self.handle_data)  # 自调用

    # ws处理器
    def handle_ws_data(self, payload):
        if "type" in payload.keys():
            if payload["type"] == "status":  # 更新modem状态
                self.bitrate.configure(text=f"BR {payload["bitrate"]}")
                self.snr.configure(text=f"SNR {payload["snr"]}")
                self.userCall.configure(text=f"UserCall {payload["user_callsign"]}")
                if self.myCallsign.get() == "":
                    self.myCallsign.set(payload["user_callsign"])
                self.destCall.configure(text=f"DestCall {payload["dest_callsign"]}")
                if payload["sync"]:  # 连接, 更新session数据
                    self.sync.config(text="SYNC", foreground="green")
                    if self.sessionTime == "":
                        self.sessionTime = datetime.datetime.now().strftime(
                            "%Y-%m-%d_%H-%M-%S"
                        )
                        self.sessionPath = os.path.join(
                            self.chatPath.get(),
                            f"{payload["dest_callsign"]}_{self.sessionTime}",
                        )
                        self.chatText.configure(state="normal")
                        self.chatText.delete("1.0", tk.END)
                        self.chatText.configure(state="disabled")
                        if not os.path.exists(self.sessionPath):
                            os.makedirs(self.sessionPath)
                else:  # 断连, 清理
                    self.sync.config(text="NO SYNC", foreground="red")
                    self.recvStat = 0
                    self.recvTime = datetime.datetime.now()
                    self.fileNameTmp = b""
                    self.lenSaved = 0
                    self.contentLenTmp = 0
                    self.dataTmp = b""
                    self.recvTmp.set("")
                    self.sessionTime = ""
                    self.sessionPath = ""
                if payload["direction"] == "rx":
                    self.direction.configure(text=f"DIR: RX", foreground="green")
                else:
                    self.direction.configure(text=f"DIR: TX", foreground="red")
                self.bytesTx.configure(text=f"TX {payload["bytes_transmitted"]}")
                self.bytesRx.configure(text=f"RX {payload["bytes_received"]}")
            elif payload["type"] == "capture_dev_list":  # 更新音频输入设备列表
                l = []
                self.audioCaptureDevices = {}
                cur = 0
                for i in range(len(payload["list"])):
                    if payload["list"][i]["id"] == payload["selected"]:
                        cur = i
                    l.append(
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    )
                    self.audioCaptureDevices[
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    ] = payload["list"][i]["id"]
                self.cptCom["values"] = l
                self.cptCom.current(cur)
            elif payload["type"] == "playback_dev_list":  # 更新音频输出设备列表
                l = []
                self.audioPlaybackDevices = {}
                cur = 0
                for i in range(len(payload["list"])):
                    if payload["list"][i]["id"] == payload["selected"]:
                        cur = i
                    l.append(
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    )
                    self.audioPlaybackDevices[
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    ] = payload["list"][i]["id"]
                self.plbkCom["values"] = l
                self.plbkCom.current(cur)
            elif payload["type"] == "input_channel":  # 更新声道选项
                self.chnCom["values"] = payload["list"]
                self.chnCom.current(payload["list"].index(payload["selected"]))
            elif payload["type"] == "radio_list":  # 更新电台设备列表
                l = []
                self.radioModels = {}
                cur = 0
                for i in range(len(payload["list"])):
                    if payload["list"][i]["id"] == payload["selected"]:
                        cur = i
                    l.append(
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    )
                    self.radioModels[
                        f"{payload["list"][i]["name"]} ({payload["list"][i]["id"]})"
                    ] = payload["list"][i]["id"]
                self.mdlCom["values"] = l
                self.mdlCom.current(cur)
                self.radioDevice.set(payload["device_path"])
                self.bdrtCom.current(
                    self.bdrtCom["values"].index(str(payload["serial_speed"]))
                )
        # 处理命令返回
        if "status" in payload.keys():
            if payload["status"] == "ok":
                messagebox.showinfo("OK", "websocket returned OK")
            elif payload["status"] == "error":
                messagebox.showerror(
                    "Error", "got an error from websocket", detail=str(payload["code"])
                )
        if "error" in payload.keys():
            messagebox.showerror(
                "Error", "Error from websocket", detail=payload["error"]
            )

    # 解析接收数据
    def parse_data_payload(self, pld):
        for b in pld:
            if self.recvStat == 0:
                self.recvTime = datetime.datetime.now()
                if b == ord("\n"):  # 文本
                    self.recvStat = 1
                elif b == ord("\r"):  # 文件
                    self.recvStat = 3
            elif self.recvStat == 1:  # 接收两位内容长度
                if self.lenSaved == 0:
                    self.contentLenTmp = b * 256
                    self.lenSaved = 1
                elif self.lenSaved == 1:
                    self.contentLenTmp += b
                    self.lenSaved = 2
                elif self.lenSaved == 2:
                    self.lenSaved = 0
                    if b == ord("\r"):
                        self.recvStat = 2
                    else:
                        messagebox.showerror("Error", "Bad data length")
                        self.recvStat = 0
                        break
            elif self.recvStat == 2:
                if b == ord("\n"):  # 文本接收完毕
                    if len(self.dataTmp) == self.contentLenTmp:
                        # 显示
                        self.chatText.configure(state="normal")
                        self.chatText.insert(
                            tk.END,
                            f"{self.recvTime.strftime("%Y-%m-%d %H:%M:%S")} recv: {self.dataTmp.decode(errors="backslashreplace")}\n",
                        )
                        self.chatText.configure(state="disabled")
                        self.chatText.see(tk.END)
                        # 落盘
                        with open(
                            os.path.join(self.sessionPath, "chat.csv"),
                            "a",
                            encoding="utf-8",
                        ) as f:
                            w = csv.writer(f)
                            w.writerow(
                                [
                                    self.recvTime.strftime("%Y-%m-%d %H:%M:%S"),
                                    "recv",
                                    "chat",
                                    self.dataTmp.decode(errors="backslashreplace"),
                                ]
                            )
                        # 清理
                        self.dataTmp = b""
                        self.recvTmp.set("")
                    else:
                        messagebox.showerror(
                            "Error",
                            "Length not equal",
                            detail=f"{len(self.dataTmp)} != {self.contentLenTmp}",
                        )
                    self.contentLenTmp = 0
                    self.recvStat = 0
                    continue
                self.dataTmp += bytes([b])
                self.recvTmp.set(
                    f"Recv: {self.dataTmp.decode(errors="backslashreplace")}"
                )
            elif self.recvStat == 3:  # 接收文件名
                if b != ord("\r"):
                    self.fileNameTmp += bytes([b])
                else:
                    self.recvStat = 4
            elif self.recvStat == 4:  # 接收两位内容长度
                if self.lenSaved == 0:
                    self.contentLenTmp = b * 256
                    self.lenSaved = 1
                elif self.lenSaved == 1:
                    self.contentLenTmp += b
                    self.lenSaved = 2
                elif self.lenSaved == 2:
                    self.lenSaved = 0
                    if b == ord("\r"):
                        self.recvStat = 5
                    else:
                        messagebox.showerror("Error", "Bad data length")
                        self.recvStat = 0
                        break
            elif self.recvStat == 5:
                if b == ord("\r") and len(self.dataTmp) == self.contentLenTmp:
                    # 显示
                    self.chatText.configure(state="normal")
                    self.chatText.insert(
                        tk.END,
                        f"{self.recvTime.strftime("%Y-%m-%d %H:%M:%S")} recv file: {self.fileNameTmp.decode(errors="backslashreplace")}\n",
                    )
                    self.chatText.configure(state="disabled")
                    self.chatText.see(tk.END)
                    # 落盘
                    with open(
                        os.path.join(self.sessionPath, "chat.csv"),
                        "a",
                        encoding="utf-8",
                    ) as f:
                        w = csv.writer(f)
                        w.writerow(
                            [
                                self.recvTime.strftime("%Y-%m-%d %H:%M:%S"),
                                "recv",
                                "file",
                                self.fileNameTmp.decode(errors="backslashreplace"),
                            ]
                        )
                    fp = os.path.join(
                        self.sessionPath,
                        self.recvTime.strftime("%Y-%m-%d_%H-%M-%S_")
                        + self.fileNameTmp.decode(errors="backslashreplace"),
                    )
                    with open(fp, "wb") as savefile:
                        savefile.write(self.dataTmp)
                    self.recvTmp.set(f"File saved: {fp}.")
                    # 清理
                    self.dataTmp = b""
                    self.fileNameTmp = b""
                    self.contentLenTmp = 0
                    self.recvStat = 0
                    continue
                self.dataTmp += bytes([b])
                self.recvTmp.set(
                    f"Recv file: {self.fileNameTmp.decode(errors="backslashreplace")} ({len(self.dataTmp)} / {self.contentLenTmp})"
                )


# 实话实说, 这个python文件太大了, Pylance 和 Black Formatter 都卡了
