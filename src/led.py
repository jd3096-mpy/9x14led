import is31
import framebuf
from machine import SoftI2C, Pin

class Display:
    """
    IS31 LED Matrix + FrameBuffer 封装库
    分辨率：9 x 16
    灰度：0~255
    """

    WIDTH = 9
    HEIGHT = 16

    def __init__(
        self,
        scl=1,
        sda=0,
        rotate_180=False,
        i2c=None,
        font="font16.fon"
    ):
        # ---------- I2C ----------
        if i2c is None:
            self.i2c = SoftI2C(
                scl=Pin(scl),
                sda=Pin(sda)
            )
        else:
            self.i2c = i2c

        # ---------- LED Driver ----------
        self.led = is31.Matrix(self.i2c, rotate_180=rotate_180)

        # ---------- FrameBuffer ----------
        self.buf = bytearray(self.WIDTH * self.HEIGHT)
        self.fb = framebuf.FrameBuffer(
            self.buf,
            self.WIDTH,
            self.HEIGHT,
            framebuf.GS8_V
        )

        # ---------- Font ----------
        try:
            self.fb.font_load(font)
        except:
            pass

    # ================= 基础操作 =================

    def clear(self, val=0):
        """清屏"""
        self.fb.fill(val)

    def show(self):
        """将 FrameBuffer 内容刷新到 LED"""
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                idx = y * self.WIDTH + x
                b = self.buf[idx]
                # 注意：IS31 的 X/Y 映射
                self.led.pixel(y, self.WIDTH - x - 1, b)

    def font(self, font_id=0x22, rotate=0, scale=1, invert=0):
        """
        设置字体
        """
        self.fb.font_set(font_id, rotate, scale, invert)

