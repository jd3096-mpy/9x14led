import bluetooth

class BLETextReceiver:
    def __init__(self, device_name="MPY-LED-BLE", callback=None):
        """
        callback(event, data)
        events:
            "conn"     - BLE连接
            "disc"     - BLE断开
            "text"     - 收到字符串 data=str
        """
        self.callback = callback
        self.device_name = device_name

        self._IRQ_CENTRAL_CONNECT = 1
        self._IRQ_CENTRAL_DISCONNECT = 2
        self._IRQ_GATTS_WRITE = 3

        self._init_ble()

    def _init_ble(self):
        self.ble = bluetooth.BLE()
        self.ble.active(True)

        UART = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        UART_TX = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
        UART_RX = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

        flags = bluetooth.FLAG_WRITE
        notify = bluetooth.FLAG_NOTIFY

        services = (
            (UART, ( (UART_TX, notify), (UART_RX, flags), )),
        )

        handles = self.ble.gatts_register_services(services)
        self.tx_handle, self.rx_handle = handles[0]

        self.conn_handle = None

        self.ble.irq(self._irq)

        name_payload = self._make_payload(self.device_name)
        self.ble.gap_advertise(100_000, name_payload)

    def _make_payload(self, name):
        p = bytearray()
        p.extend(bytes((len(name) + 1, 0x09))) 
        p.extend(name.encode())
        return p

    def _irq(self, event, data):
        if event == self._IRQ_CENTRAL_CONNECT:
            self.conn_handle, *_ = data
            if self.callback:
                self.callback("conn", None)

        elif event == self._IRQ_CENTRAL_DISCONNECT:
            self.conn_handle = None
            self.ble.gap_advertise(100_000, self._make_payload(self.device_name))
            if self.callback:
                self.callback("disc", None)

        elif event == self._IRQ_GATTS_WRITE:
            conn, value_handle = data
            if value_handle == self.rx_handle:
                raw = self.ble.gatts_read(self.rx_handle)
                try:
                    text = raw.decode()
                except:
                    text = raw.decode("latin1")

                if self.callback:
                    self.callback("text", text)

                if self.conn_handle:
                    try:
                        self.ble.gatts_notify(self.conn_handle, self.tx_handle, b"SAVED")
                    except:
                        pass
