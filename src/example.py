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