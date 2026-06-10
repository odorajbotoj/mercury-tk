import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

import datetime, os

import serial.tools.list_ports as serial_list_ports

import adif


class MTkSettings:
    def __init__(self, win, net, q):
        self.net = net
        self.uiQ = q  # queue
        self.audioCaptureDevices = {}  # 存放音频输入设备的 name - id 对应
        self.audioPlaybackDevices = {}  # 存放音频输出设备的 name - id 对应
        self.radioModels = {}  # 存放 hamlib 设备类型的 name - id 对应
        self.txGainReady = datetime.datetime.now()
        self.draw_win(win)

    # UI
    def draw_win(self, win):
        # settings notebook
        settingsNotebook = ttk.Notebook(win)
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
        self.dvcCom.bind("<Button-1>", self.cb_update_serial_port)
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
        # separator
        ttk.Separator(audioSettings).grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(10, 10)
        )
        # Tx Gain
        ttk.Label(audioSettings, text="TX Gain").grid(row=4, column=0)
        self.txGain = tk.Scale(
            audioSettings,
            from_=-20,
            to=20,
            resolution=0.1,
            orient="horizontal",
            command=self.cb_update_tx_gain,
        )
        self.txGain.grid(row=4, column=1, sticky="ew")
        self.peakDBFS = ttk.Label(audioSettings, text="Peak dBFS 0.0")
        self.peakDBFS.grid(row=6, column=1)

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
        dateEntry.bind("<Button-1>", self.cb_update_log_date)
        dateEntry.bind("<FocusIn>", self.cb_update_log_date)
        ttk.Label(logSettings, text="UTC Time").grid(row=3, column=0)  # time
        self.logTime = tk.StringVar(logSettings)
        timeEntry = ttk.Entry(logSettings, textvariable=self.logTime)
        timeEntry.grid(row=3, column=1, sticky="ew")
        timeEntry.bind("<Button-1>", self.cb_update_log_time)
        timeEntry.bind("<FocusIn>", self.cb_update_log_time)
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

    # CALLBACKS
    def cb_connect(self):
        if self.net.closed:
            self.net.connect(
                self.basePort.get(), self.kissPort.get(), self.wsPort.get()
            )
        else:
            self.net.disconnect()

    def cb_update_serial_port(self, _):
        l = []
        for i in serial_list_ports.comports():
            l.append(i.device)
        self.dvcCom["value"] = l
        self.dvcCom.current(0)

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

    def cb_update_tx_gain(self, value):
        if self.net.closed:
            return
        self.net.dataQ.put(
            {
                "dest": "ws",
                "payload": {"command": "set_tx_gain", "value": value},
            }
        )
        self.txGainReady = datetime.datetime.now()

    def browse_chat_path(self):
        self.chatPath.set(
            filedialog.askdirectory(
                initialdir=self.chatPath.get(), title="Select directory to save chat..."
            )
        )
        if not os.path.exists(self.chatPath.get()):
            os.makedirs(self.chatPath.get())
        self.uiQ.put({"type": "var", "target": "path", "value": self.chatPath.get()})

    def browse_adif(self):
        self.adifPath.set(
            filedialog.asksaveasfilename(
                initialfile=self.adifPath.get(), title="Select ADIF file to save log..."
            )
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
        for i in cmds:
            self.uiQ.put({"type": "cmd", "payload": i, "direction": "send"})
        # 传出更新变量
        self.uiQ.put({"type": "var", "target": "bw", "value": self.bwCom.get()})

    def cb_update_log_date(self, _):
        self.logDate.set(
            datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        )

    def cb_update_log_time(self, _):
        self.logTime.set(
            datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S")
        )

    # DATA
    def chat_path(self):
        return self.chatPath.get()

    def get_mycallsign(self):
        return self.myCallsign.get()

    def set_mycallsign(self, c):
        self.myCallsign.set(c)

    def update_conn_btn(self, connected):
        self.connBtnText.set("Connect" if connected else "Disconnect")

    def update_capture_dev_list(self, li, sel):
        l = []
        self.audioCaptureDevices = {}
        cur = 0
        for i in range(len(li)):
            if li[i]["id"] == sel:
                cur = i
            l.append(f"{li[i]["name"]} ({li[i]["id"]})")
            self.audioCaptureDevices[f"{li[i]["name"]} ({li[i]["id"]})"] = li[i]["id"]
        self.cptCom["values"] = l
        self.cptCom.current(cur)

    def update_playback_dev_list(self, li, sel):
        l = []
        self.audioPlaybackDevices = {}
        cur = 0
        for i in range(len(li)):
            if li[i]["id"] == sel:
                cur = i
            l.append(f"{li[i]["name"]} ({li[i]["id"]})")
            self.audioPlaybackDevices[f"{li[i]["name"]} ({li[i]["id"]})"] = li[i]["id"]
        self.plbkCom["values"] = l
        self.plbkCom.current(cur)

    def update_input_channel(self, li, sel):
        self.chnCom["values"] = li
        self.chnCom.current(li.index(sel))

    def update_radio_list(self, li, sel, path, speed):
        l = []
        self.radioModels = {}
        cur = 0
        for i in range(len(li)):
            if li[i]["id"] == sel:
                cur = i
            l.append(f"{li[i]["name"]} ({li[i]["id"]})")
            self.radioModels[f"{li[i]["name"]} ({li[i]["id"]})"] = li[i]["id"]
        self.mdlCom["values"] = l
        self.mdlCom.current(cur)
        self.radioDevice.set(path)
        self.bdrtCom.current(self.bdrtCom["values"].index(str(speed)))

    def update_tx_gain(self, gain, peak):
        if datetime.datetime.now() - self.txGainReady > datetime.timedelta(seconds=3):
            self.txGain.set(gain)
        self.peakDBFS.configure(text=f"Peak dBFS {peak}")
