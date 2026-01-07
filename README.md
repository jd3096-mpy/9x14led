# micropython赛博项链

在网上看到由很多人做赛博蜡烛，索性联合老李做了一个小巧的赛博蜡烛，内置电池，加外壳可以当项链带了。

![Anise Badge](./pic.jpg)

## 程序

* 火焰动画显示
* 文字滚动显示（可由手机蓝牙ble设置，修改content.txt也可以）
* 俄罗斯方块游戏动画
* 赛车游戏动画

## 硬件

* ESP32-C4FH4 With 4MB Flash
* 602020 200毫安时电池  约2小时续航时间
* 9x14 144个pwm可调 led

## 引脚分布

* IO0: I2C_SDA: 0
* IO1: I2C_SCL: 1
* IO3: 电池电压 / 2
* IO4: 充电检测
* IO4: 按键/boot

## 购买渠道

* b站小店（原工房）
* 闲鱼

  

## 自定义内容的极简例子

```python
#导入库并初始化
from led import Display
display = Display()

#字库设置
display.fb.font_set(0x22, 0, 1, 0)   #设置字体（参数依次为为字体  旋转  放大倍数  反色） 
#按照micropython framebuf语法去写即可          
display.fb.text("S",1,1,22)     #将字符串“S” 写入坐标1,1 亮度为22 
display.fb.line(1,0,7,0,44)     #画线 从1,0 到 6,0  亮度为44
display.fb.line(1,15,7,15,44)     #画线 从1,15 到 6,15  亮度为44
display.show()
```

