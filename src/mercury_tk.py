import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import datetime, os, csv, queue

# user-define
import kiss
import mtk_net

# ui
from ui_settings import MTkSettings
from ui_chat import MTkChat
from ui_status import MTkStatus
from ui_waterfall import MTkWaterfall


class MercuryTk:  # 主 ui 绘制
    def __init__(self, v):
        self.VERSION = v
        self.uiQ = queue.Queue()
        self.net = mtk_net.MTkNet(self.uiQ)

        self.recvStat = 0  # 0 Idle, 1 Len, 2 Str, 3 Name, 4 Size, 5 File
        self.recvTime = datetime.datetime.now()  # 接收到数据的时间
        self.fileNameTmp = b""  # 接收到的文件名 (缓冲区)
        self.lenSaved = 0  # 接收数据长度的状态
        self.contentLenTmp = 0  # 接收数据长度 (缓冲区)
        self.dataTmp = b""  # 接收数据缓冲区

        self.callsign = ""

        # main window
        self.window = tk.Tk()
        self.window.title("mercury-tk")
        self.window.geometry("1024x768+10+10")
        self.window.grid_rowconfigure(2, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self.frame_settings = MTkSettings(self.window, self.net, self.uiQ)
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=1, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        self.frame_chat = MTkChat(self.window, self.net, self.callsign, self.VERSION)
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=3, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        self.frame_status = MTkStatus(self.window)
        # separator
        ttk.Separator(self.window, orient="horizontal").grid(
            row=5, column=0, sticky="ew", padx=(10, 10), pady=(10, 10)
        )

        # waterfall
        self.frame_waterfall = MTkWaterfall(self.window)

        # 创建历史保存文件夹
        if not os.path.exists(self.frame_settings.chat_path()):
            os.makedirs(self.frame_settings.chat_path())

    # 主App运行
    def run(self):
        self.handle_data()
        self.window.mainloop()

    # 处理数据
    def handle_data(self):
        while not self.uiQ.empty():
            data = self.uiQ.get()
            if data["type"] == "modem":  # 更新连接状态
                if data["connected"]:
                    self.frame_settings.update_conn_btn(False)
                    self.frame_status.update_conn_stat("MODEM CONNECTED", "green")
                else:
                    self.frame_settings.update_conn_btn(True)
                    self.frame_status.update_conn_stat("MODEM DISCONNECTED", "red")
                    messagebox.showerror(
                        title="Error",
                        message="Modem disconnected",
                        detail=data["detail"],
                    )
            elif data["type"] == "ws":  # 交给ws处理器
                self.handle_ws_data(data["payload"])
            elif data["type"] == "waterfall":  # 交给瀑布图处理器
                self.frame_waterfall.draw(data["payload"])
            elif data["type"] == "cmd":  # 追加到命令历史框, 两个特殊命令做额外处理
                self.frame_chat.append_to_text(
                    "cmd",
                    [
                        f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {data["direction"]}: {data["payload"]}\n"
                    ],
                )
                if data["payload"].startswith("CQFRAME"):
                    self.frame_chat.append_to_text(
                        "cq",
                        [
                            f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {data["direction"]}: {data["payload"]}\n"
                        ],
                    )
                elif data["payload"].startswith("BUFFER"):
                    self.frame_chat.update_recv_tmp(
                        f"Data remaining: {data["payload"][7:]}"
                    )
            elif data["type"] == "data":  # 交给数据处理器
                self.parse_data_payload(data["payload"])
            elif data["type"] == "kiss":  # 处理广播包
                l = kiss.kiss_decode(data["payload"])
                dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s = []
                for pld in l:
                    s.append(f"{dt} recv: {pld.decode(errors="backslashreplace")}\n")
                self.frame_chat.append_to_text("bcast", s)
                with open(
                    os.path.join(self.frame_settings.chat_path(), "broadcast.csv"),
                    "a",
                    encoding="utf-8",
                ) as f:
                    for pld in l:
                        w = csv.writer(f)
                        w.writerow([dt, "recv", pld.decode(errors="backslashreplace")])
            elif data["type"] == "var":  # 更新变量
                if data["target"] == "bw":
                    self.frame_chat.update_bandwidth(data["value"])
                elif data["target"] == "path":
                    self.frame_chat.update_chat_path(data["value"])
        self.window.after(50, self.handle_data)  # 自调用

    # ws处理器
    def handle_ws_data(self, payload):
        try:
            if "type" in payload.keys():
                if payload["type"] == "status":  # 更新modem状态
                    self.frame_status.update_connection_stat(
                        payload["bitrate"],
                        payload["snr"],
                        payload["user_callsign"],
                        payload["dest_callsign"],
                        payload["bytes_transmitted"],
                        payload["bytes_received"],
                    )
                    if self.callsign != payload["user_callsign"]:
                        self.callsign = payload["user_callsign"]
                        self.frame_settings.set_mycallsign(self.callsign)
                        self.frame_chat.set_mycallsign(self.callsign)
                    if payload["sync"]:  # 连接, 更新session数据
                        self.frame_status.update_sync_stat("SYNC", "green")
                        if self.sessionTime == "":
                            self.sessionTime = datetime.datetime.now().strftime(
                                "%Y-%m-%d_%H-%M-%S"
                            )
                            self.sessionPath = os.path.join(
                                self.frame_settings.chat_path(),
                                f"{payload["dest_callsign"]}_{self.sessionTime}",
                            )
                            self.frame_chat.clear_chat_text()
                            if not os.path.exists(self.sessionPath):
                                os.makedirs(self.sessionPath)
                    else:  # 断连, 清理
                        self.frame_status.update_sync_stat("NO SYNC", "red")
                        self.recvStat = 0
                        self.recvTime = datetime.datetime.now()
                        self.fileNameTmp = b""
                        self.lenSaved = 0
                        self.contentLenTmp = 0
                        self.dataTmp = b""
                        self.frame_chat.update_recv_tmp("")
                        self.sessionTime = ""
                        self.sessionPath = ""
                    if payload["direction"] == "rx":
                        self.frame_status.update_direction_stat("DIR: RX", "green")
                    else:
                        self.frame_status.update_direction_stat("DIR: TX", "red")
                    self.frame_settings.update_tx_gain(
                        payload["tx_gain_db"], payload["tx_peak_dbfs"]
                    )
                elif payload["type"] == "capture_dev_list":  # 更新音频输入设备列表
                    self.frame_settings.update_capture_dev_list(
                        payload["list"], payload["selected"]
                    )
                elif payload["type"] == "playback_dev_list":  # 更新音频输出设备列表
                    self.frame_settings.update_playback_dev_list(
                        payload["list"], payload["selected"]
                    )
                elif payload["type"] == "input_channel":  # 更新声道选项
                    self.frame_settings.update_input_channel(
                        payload["list"], payload["selected"]
                    )
                elif payload["type"] == "radio_list":  # 更新电台设备列表
                    self.frame_settings.update_radio_list(
                        payload["list"],
                        payload["selected"],
                        payload["device_path"],
                        payload["serial_speed"],
                    )
            # 处理命令返回
            if "status" in payload.keys():
                if payload["status"] == "ok":
                    # messagebox.showinfo("OK", "websocket returned OK")
                    pass
                elif payload["status"] == "error":
                    messagebox.showerror(
                        "Error",
                        "got an error from websocket",
                        detail=str(payload["code"]),
                    )
            if "error" in payload.keys():
                messagebox.showerror(
                    "Error", "Error from websocket", detail=payload["error"]
                )
        except Exception as e:
            messagebox.showerror(
                "Error", "failed to parse data from mercury", detail=str(e)
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
                        self.frame_chat.append_to_text(
                            "chat",
                            [
                                f"{self.recvTime.strftime("%Y-%m-%d %H:%M:%S")} recv: {self.dataTmp.decode(errors="backslashreplace")}\n"
                            ],
                        )
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
                        self.frame_chat.update_recv_tmp("")
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
                self.frame_chat.update_recv_tmp(
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
                if len(self.dataTmp) == self.contentLenTmp:
                    if b != ord("\r"):
                        messagebox.showerror("Error", "Bad file data")
                        self.dataTmp = b""
                        self.fileNameTmp = b""
                        self.contentLenTmp = 0
                        self.recvStat = 0
                        break
                    # 显示
                    self.frame_chat.append_to_text(
                        "chat",
                        [
                            f"{self.recvTime.strftime("%Y-%m-%d %H:%M:%S")} recv file: {self.fileNameTmp.decode(errors="backslashreplace")}\n"
                        ],
                    )
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
                    self.frame_chat.update_recv_tmp(f"File saved: {fp}.")
                    # 清理
                    self.dataTmp = b""
                    self.fileNameTmp = b""
                    self.contentLenTmp = 0
                    self.recvStat = 0
                    continue
                self.dataTmp += bytes([b])
                self.frame_chat.update_recv_tmp(
                    f"Recv file: {self.fileNameTmp.decode(errors="backslashreplace")} ({len(self.dataTmp)} / {self.contentLenTmp})"
                )
