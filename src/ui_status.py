from tkinter import ttk


class MTkStatus:
    def __init__(self, win):
        self.draw_win(win)

    # UI
    def draw_win(self, win):
        # status
        statusFrame = ttk.Frame(win)
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

    # DATA
    def update_conn_stat(self, val, col):
        self.connStat.configure(text=val, foreground=col)

    def update_sync_stat(self, val, col):
        self.sync.config(text=val, foreground=col)

    def update_direction_stat(self, val, col):
        self.direction.configure(text=val, foreground=col)

    def update_connection_stat(self, br, snr, userCS, destCS, btx, brx):
        self.bitrate.configure(text=f"BR {br}")
        self.snr.configure(text=f"SNR {snr}")
        self.userCall.configure(text=f"UserCall {userCS}")
        self.destCall.configure(text=f"DestCall {destCS}")
        self.bytesTx.configure(text=f"TX {btx}")
        self.bytesRx.configure(text=f"RX {brx}")
