import tkinter.messagebox

freq_wl_map = [
    ["2190m", 0.1357, 0.1378],
    ["630m", 0.472, 0.479],
    ["560m", 0.501, 0.504],
    ["160m", 1.8, 2],
    ["80m", 3.5, 4],
    ["60m", 5.06, 5.45],
    ["40m", 7, 7.3],
    ["30m", 10.1, 10.15],
    ["20m", 14, 14.35],
    ["17m", 18.068, 18.168],
    ["15m", 21, 21.45],
    ["12m", 24.89, 24.99],
    ["10m", 28, 29.7],
    ["8m", 40, 45],
    ["6m", 50, 54],
    ["5m", 54.000001, 69.9],
    ["4m", 70, 71],
    ["2m", 144, 148],
    ["1.25m", 222, 225],
    ["70cm", 420, 450],
    ["33cm", 902, 928],
    ["23cm", 1240, 1300],
    ["13cm", 2300, 2450],
    ["9cm", 3300, 3500],
    ["6cm", 5650, 5925],
    ["3cm", 10000, 10500],
    ["1.25cm", 24000, 24250],
    ["6mm", 47000, 47200],
    ["4mm", 75500, 81000],
    ["2.5mm", 119980, 123000],
    ["2mm", 134000, 149000],
    ["1mm", 241000, 250000],
    ["submm", 300000, 7500000],
]


def log_to_adif(filepath, call, da, ti, freq, rxfreq):
    band = ""
    rxband = ""
    for b in freq_wl_map:
        if b[2] < freq:
            continue
        else:
            band = b[0]
            break
    for b in freq_wl_map:
        if b[2] < rxfreq:
            continue
        else:
            rxband = b[0]
            break

    try:
        with open(filepath, "a+", encoding="utf-8") as f:
            f.write(
                f"<CALL:{len(call)}>{call} <BAND:{len(band)}>{band} <MODE:3>PKT <QSO_DATE:{len(da)}>{da} <TIME_ON:{len(ti)}>{ti} <FREQ:{len(str(freq))}>{str(freq)} <BAND_RX:{len(rxband)}>{rxband} <FREQ_RX:{len(str(rxfreq))}>{str(rxfreq)} <EOR>\n"
            )
        tkinter.messagebox.showinfo(
            title="Added log to file",
            message="Success",
            detail=f"{call}\n{da}\n{ti}\n<-{band}: {freq}MHz\n->{rxband}: {rxfreq}MHz",
        )
    except Exception as e:
        tkinter.messagebox.showerror(
            title="Failed to add log to file", message="Error", detail=repr(e)
        )
