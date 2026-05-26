# mercury-tk

A **rough** (and maybe **unsafe**) ui client for [Mercury HF Modem](https://github.com/Rhizomatica/mercury)

written in **Python3.13** with `tkinter` , `pillow` , `numpy` , `websocket-client`, `pyserial`.

by BG4QBF

## Features

+ set Mercury audio and radio devices
+ CQ and connect
+ chat and send file
+ broadcast
+ simple chat history save
+ simple QSO LOG save (ADIF)
+ waterfall

## Using

1. install and run Mercury (need `-G` to open websocket service)
2. install requirements and run this app
3. enter the ports and click `Connect`
4. set radio devices and audio devices
5. set callsign and bandwidth
6. set history and log saving path
7. CQ, send broadcast, connect to other radio and make QSO
8. if necessary, log to ADIF file

## Data structure

Chat message:

```text
\n[length // 256][length % 256]\r[message]\n
```

File:

```text
\r[file name]\r[length // 256][length % 256]\r[file content]\r
```

## Coding Assistant

+ Xiaomi mimo v2.5 (opencode) for reading source code of Mercury

## License

MIT
