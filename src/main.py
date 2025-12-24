import is31
from machine import SoftI2C, Pin, ADC
import time, random, framebuf ,math
from ble_text import BLETextReceiver

class GameContext:
    WIDTH = 9
    HEIGHT = 16

    VREF = 3.3
    DIV_RATIO = 2.0
    FULL = 4.20
    EMPTY = 3.30
    SAMPLES = 16
    HYST = 0.3

    BRIGHT = 100
    DARK = 0
    CAR_COLOR = 160
    ENEMY_COLOR = 20
    LANE_A = 1
    LANE_B = 5
    ENEMY_SPEED = 1

    CAR_SHAPE = [
        [0,1,0],
        [1,1,1],
        [0,1,0],
        [1,0,1]
    ]


    def __init__(self):
        # 显示
        i2c = SoftI2C(scl=Pin(1), sda=Pin(0))
        self.display = is31.Matrix(i2c, rotate_180=True)
        self.display.fill(0)

        # 按键
        self.key = Pin(9, Pin.IN, Pin.PULL_UP)
        self._button_raw = self.key.value()        
        self._button_stable = self._button_raw     
        self._button_prev_stable = self._button_raw
        self._button_last_change = time.ticks_ms()
        self._debounce_ms = 50                     

        # 电压
        self.adc = ADC(Pin(3))
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_12BIT)
        self.last_level = 0

        # framebuf
        self.fb_buf = bytearray(self.WIDTH * self.HEIGHT)
        self.fb = framebuf.FrameBuffer(self.fb_buf, self.WIDTH, self.HEIGHT, framebuf.GS8_V)
        self.fb.font_load("font16.fon")
        self.fb.font_set(0x22, 0, 1, 0)

        # 动画
        self.fire_file = open("anim.bin", "rb")

        # 赛车状态
        self.player_lane = self.LANE_A
        self.player_y = self.HEIGHT - 5
        self.enemy_list = []
        self.gap_count = random.randint(5, 16)
        self.shoulder_offset = 0


    # =====================================================================
    #                              工具函数
    # =====================================================================
    def debounce_key(self):
        now = time.ticks_ms()
        raw = self.key.value() 

        if raw != self._button_raw:
            self._button_raw = raw
            self._button_last_change = now
            return False

        if time.ticks_diff(now, self._button_last_change) >= self._debounce_ms:
            if raw != self._button_stable:
                self._button_prev_stable = self._button_stable
                self._button_stable = raw
                if self._button_prev_stable == 0 and self._button_stable == 1:
                    return True

        return False


    def fb_show(self):
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                idx = y * self.WIDTH + x
                b = self.fb_buf[idx]
                self.display.pixel(y, self.WIDTH - x - 1, b)

    # =====================================================================
    #                            App：测试用不放入正式程序里
    # =====================================================================
    def app_charge(self):
        self.fb.font_set(0x11, 0, 0, 0)
        cha = Pin(10,Pin.IN,Pin.PULL_UP)
        full = Pin(10,Pin.IN,Pin.PULL_UP)
        while 1:
            self.fb.fill(0)
            if cha.value()==1:
                self.fb.text("c", 0, 0, 10)
            else:
                self.fb.text("bc", 0, 0, 10)
            self.fb_show()
            time.sleep(1)
            
    # =====================================================================
    #                               App：火焰动画
    # =====================================================================
    def app_fire(self):
        self.display.fill(0)
        f = self.fire_file
        w, h = 7, 15
        delay = 0.015

        def read_byte():
            b = f.read(1)
            if not b:
                f.seek(0)
                b = f.read(1)
            return b[0]

        while True:
            a = read_byte()
            if a >= 0x90:
                f.seek(0)
                a = read_byte()

            x1, y1 = a >> 4, a & 0x0F
            a = read_byte()
            x2, y2 = a >> 4, a & 0x0F

            for y in range(h):
                for x in range(w):
                    if x1 <= x <= x2 and y1 <= y <= y2:
                        color = read_byte()
                    else:
                        color = 0
                    new_y = h - 1 - y
                    self.display.pixel(new_y+1, x+1, color)

            time.sleep(delay)
            if self.debounce_key(): break


    # =====================================================================
    #                             App：滚动文字
    # =====================================================================
    def app_scroll_text(self, filename="content.txt"):
        self.fb.font_set(0x22, 0, 1, 0)
        try:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read().strip()
        except:
            text = "FILE ERROR"

        def char_width(c):
            return 16 if '\u4e00' <= c <= '\u9fff' else 8

        def fb_to_display():
            for y in range(self.HEIGHT):
                for x in range(self.WIDTH):
                    idx = y * self.WIDTH + x
                    b = self.fb_buf[idx]
                    self.display.pixel(y, self.WIDTH - x - 1, b)

                    shadow_x = x + 1
                    shadow_y = y + 1
                    if shadow_x < self.WIDTH and shadow_y < self.HEIGHT:
                        shadow_idx = shadow_y * self.WIDTH + shadow_x
                        if self.fb_buf[shadow_idx] == 0:
                            shadow_b = max(b - 45, 0)
                            self.fb_buf[shadow_idx] = shadow_b

        # 外层循环：一直滚动，直到按键按下并松开
        exit_flag = False
        key_was_pressed = False

        while not exit_flag:
            text_width = sum(char_width(c) for c in text)
            for offset in range(text_width + self.WIDTH):
                self.fb.fill(0)
                x = self.WIDTH - offset
                for c in text:
                    self.fb.text(c, x, 0, 60)
                    x += char_width(c)

                fb_to_display()
                time.sleep(0.01)

                # 按键检测：按下 -> 设置标志，抬起 -> 退出
                if self.key.value() == 0:  # 按下
                    key_was_pressed = True
                elif key_was_pressed and self.key.value() == 1:  # 松开
                    exit_flag = True
                    break
    
    # =====================================================================
    #                            App：电池电量
    # =====================================================================
    def read_battery_level(self):
        def read_voltage_once():
            total = 0
            for _ in range(self.SAMPLES):
                total += self.adc.read_u16()
                time.sleep_us(200)
            adc_v = (total / self.SAMPLES) * self.VREF / 65535
            return adc_v * self.DIV_RATIO

        readings = 5
        v_total = 0
        for _ in range(readings):
            v_total += read_voltage_once()
            time.sleep_ms(5)

        v = v_total / readings

        if v >= self.FULL:
            lvl = 99
        elif v <= self.EMPTY:
            lvl = 0
        else:
            lvl = (v - self.EMPTY) / (self.FULL - self.EMPTY) * 100

        if abs(lvl - self.last_level) >= self.HYST:
            self.last_level = lvl

        return int(self.last_level)
    
    def charging_loop(self):
        W = self.WIDTH      # 9
        H = self.HEIGHT     # 16

        # ===== 电池几何（7x12，居中）=====
        xL, xR = 1, 7           # 外壳
        xInL, xInR = 2, 6       # 内腔（5）

        cap_y = 2               # 电池帽
        cap_x1, cap_x2 = 3, 5

        shell_top = 3
        shell_bottom = 12

        inner_top = 4
        inner_bottom = 11
        inner_h = inner_bottom - inner_top + 1   # 8 行

        shell_b = 70
        cap_b = 110

        # ===== 填充亮度参数 =====
        BASE_BRIGHT = 70        # 最底部
        STEP = 10               # 每行递减

        fill = 0                # 当前填充高度（0~inner_h）

        while True:
            # 一旦开机，退出充电动画
            if self.read_battery_level() > 0:
                self.display.fill(0)
                return

            # ===== 每一帧都推进填充 =====
            fill += 1
            if fill > inner_h:
                fill = 0

            # 清屏
            for i in range(W * H):
                self.fb_buf[i] = 0

            # ===== 电池帽 =====
            for x in range(cap_x1, cap_x2 + 1):
                self.fb_buf[cap_y * W + x] = cap_b

            # ===== 外壳 =====
            for y in range(shell_top, shell_bottom + 1):
                self.fb_buf[y * W + xL] = shell_b
                self.fb_buf[y * W + xR] = shell_b

            for x in range(xL, xR + 1):
                self.fb_buf[shell_top * W + x] = shell_b
                self.fb_buf[shell_bottom * W + x] = shell_b

            # ===== 内部填充（明确亮度梯度）=====
            for i in range(fill):
                y = inner_bottom - i

                # 亮度：底 80 → 上每行 -10
                val = BASE_BRIGHT - i * STEP
                if val < 5:
                    val = 5

                for x in range(xInL, xInR + 1):
                    self.fb_buf[y * W + x] = val

            self.fb_show()
            time.sleep(0.05)   # 现在会非常顺滑




            
    def app_battery(self):
        self.fb.font_set(0x11, 1, 1, 0)

        lvl = self.read_battery_level()

        # === ① 充电状态 ===
        if lvl == 0:
            self.charging_loop()
            return   # 退出后重新判断一次即可

        # === ② 正常开机状态 ===
        self.fb.fill(0)
        s = f"{lvl:02d}"
        self.fb.text(s[1], -3, 0, 100)
        self.fb.text(s[0], -3, 5, 100)
        self.fb.text("%", -3, 10, 100)
        self.fb_show()

        time.sleep(1.5)
        self.display.fill(0)


    # =====================================================================
    #                            App：赛车游戏
    # =====================================================================
    def app_race(self):

        def draw_car(x, y, color):
            for dy in range(4):
                if y + dy >= self.HEIGHT: continue
                for dx in range(3):
                    if self.CAR_SHAPE[dy][dx]:
                        xx = x + dx
                        if 0 <= xx < self.WIDTH:
                            self.fb_buf[(y + dy)*self.WIDTH + xx] = color

        def draw_shoulders():
            base = self.shoulder_offset
            for y in range(self.HEIGHT):
                mode = (y + base) % 5
                col = self.BRIGHT if mode < 3 else self.DARK
                self.fb_buf[y*self.WIDTH + 0] = col
                self.fb_buf[y*self.WIDTH + 8] = col
            self.shoulder_offset = (self.shoulder_offset + 1) % 5

        def fb_to_display():
            for y in range(self.HEIGHT):
                base = y * self.WIDTH
                for x in range(self.WIDTH):
                    self.display.pixel(y, self.WIDTH-x-1, self.fb_buf[base+x])

        def spawn_enemy():
            lane = self.LANE_A if random.getrandbits(1) == 0 else self.LANE_B
            self.enemy_list.append({"x": lane, "y": -4})

        def move_enemies():
            for e in self.enemy_list:
                e["y"] += self.ENEMY_SPEED
            self.enemy_list[:] = [e for e in self.enemy_list if e["y"] < self.HEIGHT]

        def will_collide(lane):
            for e in self.enemy_list:
                if e["x"] == lane:
                    if self.player_y <= e["y"] + 3 and e["y"] <= self.player_y + 3:
                        return True
            return False

        def ai_update():
            if will_collide(self.player_lane):
                other = self.LANE_B if self.player_lane == self.LANE_A else self.LANE_A
                if not will_collide(other):
                    self.player_lane = other

        def draw_all():
            for i in range(self.WIDTH * self.HEIGHT):
                self.fb_buf[i] = 0

            draw_shoulders()
            for e in self.enemy_list:
                draw_car(e["x"], int(e["y"]), self.ENEMY_COLOR)
            draw_car(self.player_lane, self.player_y, self.CAR_COLOR)
            fb_to_display()

        while True:
            if self.gap_count <= 0:
                spawn_enemy()
                self.gap_count = random.randint(4, 8)
            else:
                self.gap_count -= 1

            move_enemies()
            ai_update()
            draw_all()

            if self.debounce_key(): break
            
    def app_tetris_ai(self):
        W = self.WIDTH     
        H = self.HEIGHT    
        FRAME_DELAY = 0.02
        PALETTE = {'I':220,'O':170,'T':150,'S':100,'Z':80,'J':40,'L':20,' ':0}

        def empty_grid():
            return [[0]*W for _ in range(H)]

        def clone_grid(g):
            return [row[:] for row in g]

        def can_place(grid, shape, x, y):
            sh = len(shape); sw = len(shape[0])
            for ry in range(sh):
                for rx in range(sw):
                    if shape[ry][rx]:
                        gx = x + rx; gy = y + ry
                        if gx < 0 or gx >= W or gy < 0 or gy >= H: return False
                        if grid[gy][gx] != 0: return False
            return True

        def place_on(grid, shape, x, y, val):
            for ry in range(len(shape)):
                for rx in range(len(shape[0])):
                    if shape[ry][rx]:
                        gx = x + rx; gy = y + ry
                        if 0 <= gx < W and 0 <= gy < H:
                            grid[gy][gx] = val

        def clear_lines(grid):
            new = []
            cleared = 0
            for row in grid:
                if all(v != 0 for v in row):
                    cleared += 1
                else:
                    new.append(row)
            while len(new) < H:
                new.insert(0, [0]*W)
            return new, cleared

        def rotate90(m):
            h = len(m); w = len(m[0])
            out = [[0]*h for _ in range(w)]
            for y in range(h):
                for x in range(w):
                    out[x][h-1-y] = m[y][x]
            return out

        def normalize(mat):
            h=len(mat); w=len(mat[0])
            top=0; bottom=h-1; left=0; right=w-1
            while top <= bottom and all(v == 0 for v in mat[top]): top += 1
            while bottom >= top and all(v == 0 for v in mat[bottom]): bottom -= 1
            while left <= right and all(mat[r][left] == 0 for r in range(h)): left += 1
            while right >= left and all(mat[r][right] == 0 for r in range(h)): right -= 1
            if top > bottom or left > right:
                return [[0]]
            return [mat[r][left:right+1] for r in range(top, bottom+1)]

        def equal(a,b):
            if len(a)!=len(b) or len(a[0])!=len(b[0]): return False
            for y in range(len(a)):
                for x in range(len(a[0])):
                    if a[y][x]!=b[y][x]: return False
            return True

        def rotations(mat):
            r=[]
            cur = normalize(mat)
            r.append(cur)
            for _ in range(3):
                cur = rotate90(cur)
                cur = normalize(cur)
                if not any(equal(cur, x) for x in r):
                    r.append(cur)
            return r

        TETROMINO = {
            'I':[[1,1,1,1]],
            'O':[[1,1],[1,1]],
            'T':[[0,1,0],[1,1,1]],
            'S':[[0,1,1],[1,1,0]],
            'Z':[[1,1,0],[0,1,1]],
            'J':[[1,0,0],[1,1,1]],
            'L':[[0,0,1],[1,1,1]]
        }

        PIECES = {k:rotations(v) for k,v in TETROMINO.items()}

        # ---------- 评估与 AI ----------
        def count_holes(g):
            holes = 0
            for x in range(W):
                filled = False
                for y in range(H):
                    if g[y][x] != 0:
                        filled = True
                    elif filled:
                        holes += 1
            return holes

        def col_heights(g):
            hts=[0]*W
            for x in range(W):
                for y in range(H):
                    if g[y][x]:
                        hts[x]=H-y
                        break
            return hts

        def eval_grid(grid, lines):
            hts = col_heights(grid)
            agg = sum(hts)
            holes = count_holes(grid)
            score = lines*500 - holes*300 - agg*5
            return score

        def choose_best(grid, key):
            best_move=None
            best_score=-999999
            for ri,shape in enumerate(PIECES[key]):
                sh=len(shape); sw=len(shape[0])
                for x in range(-sw+1, W):
                    y=0
                    if not can_place(grid, shape, x, y): continue
                    while can_place(grid, shape, x, y+1): y+=1
                    temp = clone_grid(grid)
                    place_on(temp, shape, x, y, 1)
                    temp2, lines = clear_lines(clone_grid(temp))
                    score = eval_grid(temp2, lines)
                    if score > best_score:
                        best_score = score
                        best_move = (ri, x, y)
            return best_move

        def compose_pixels(grid, shape=None, pos=None, val=120):
            pixels = [[0]*W for _ in range(H)]
            for y in range(H):
                for x in range(W):
                    if grid[y][x]:
                        pixels[y][x] = grid[y][x]
 
            if shape and pos:
                px, py = pos
                for ry in range(len(shape)):
                    for rx in range(len(shape[0])):
                        if shape[ry][rx]:
                            gx = px + rx; gy = py + ry
                            if 0 <= gx < W and 0 <= gy < H:
                                pixels[gy][gx] = val
            return pixels

        def draw_pixels(pixels):
            for y in range(H):
                for x in range(W):
                    color = pixels[y][x]
                    self.display.pixel(y, x, color)


        def flash_lines_and_clear(grid, lines, flashes=2, delay=0.12):
            for _ in range(flashes):
                temp = compose_pixels(grid, None, None)
                for y in lines:
                    for x in range(W):
                        temp[y][x] = 0
                draw_pixels(temp)
                time.sleep(delay)

                temp = compose_pixels(grid, None, None)
                for y in lines:
                    for x in range(W):
                        temp[y][x] = PALETTE.get('O', 150)
                draw_pixels(temp)
                time.sleep(delay)

            new_grid, cnt = clear_lines(grid)
            return new_grid, cnt

        while True:
            grid = empty_grid()
            frame = 0
            cur = None
            px = py = 0
            shape = None

            while True:
                if self.debounce_key():
                    return

                if any(grid[0][x] != 0 for x in range(W)):
                    draw_pixels([[0]*W for _ in range(H)])
                    time.sleep(0.3)
                    break

                if cur is None:
                    key = random.choice(list(PIECES.keys()))
                    rots = PIECES[key]
                    rot_idx = 0
                    shape = rots[rot_idx]
                    px = (W - len(shape[0])) // 2
                    py = 0

                    best = choose_best(grid, key)
                    if best:
                        target_rot, target_x, _ = best
                    else:
                        target_rot, target_x = rot_idx, px

                    cur = {
                        "key": key,
                        "rots": rots,
                        "rot_idx": rot_idx,
                        "target_rot": target_rot,
                        "target_x": target_x,
                        "val": PALETTE.get(key, 120)
                    }
                    shape = rots[cur["rot_idx"]]

                if frame % 1 == 0 and cur:
                    if py > 0 and cur["rot_idx"] != cur["target_rot"]:
                        all_rots = cur["rots"]
                        mod = len(all_rots)
                        cur_idx = cur["rot_idx"]
                        target = cur["target_rot"]
                        if (target - cur_idx) % mod <= (cur_idx - target) % mod:
                            nxt = (cur_idx + 1) % mod
                        else:
                            nxt = (cur_idx - 1) % mod
                        nxt_shape = all_rots[nxt]
                        for kx in (0, -1, 1):
                            if can_place(grid, nxt_shape, px + kx, py):
                                px += kx
                                cur["rot_idx"] = nxt
                                shape = nxt_shape
                                break

                    if px < cur["target_x"]:
                        if can_place(grid, shape, px+1, py):
                            px += 1
                    elif px > cur["target_x"]:
                        if can_place(grid, shape, px-1, py):
                            px -= 1
                            
                    if can_place(grid, shape, px, py+1):
                        py += 1
                    else:
                        place_on(grid, shape, px, py, cur["val"])
                        full_lines = [y for y in range(H) if all(grid[y][x] != 0 for x in range(W))]
                        if full_lines:
                            grid, _ = flash_lines_and_clear(grid, full_lines, flashes=2, delay=0.12)
                        cur = None
                        shape = None

                pixels = compose_pixels(grid, shape, (px, py) if shape else None, cur["val"] if cur else 120)
                draw_pixels(pixels)

                frame += 1
                time.sleep(FRAME_DELAY)
                
    def app_ble(self):
        self.fb.font_set(0x12, 0, 1, 0)
        state = "idle"       
        saved_text = ""       
        exit_flag = False   

        def show(text, brightness=100):
            self.fb.fill(0)
            self.fb.text(text, 0, 1, brightness)
            for y in range(self.HEIGHT):
                base = y * self.WIDTH
                for x in range(self.WIDTH):
                    self.display.pixel(y, self.WIDTH-x-1, self.fb_buf[base+x])

        def on_ble(event, data):
            nonlocal state, saved_text, exit_flag

            if event == "conn":
                state = "connected"

            elif event == "disc":
                state = "idle"

            elif event == "text":
                saved_text = data
                state = "saved"

                with open("content.txt", "w") as f:
                    f.write(saved_text)

                if ble.conn_handle is not None:
                    try:
                        ble.ble.gap_disconnect(ble.conn_handle)
                    except:
                        pass
                exit_flag = True

        ble = BLETextReceiver("LED-BLE", callback=on_ble)

        while not exit_flag:
            if state == "idle":
                show("B")      
            elif state == "connected":
                show("C")          
            elif state == "saved":
                show("O")      
                time.sleep(1) 

            time.sleep(0.05)
            if self.debounce_key():     
                break

    def run(self):
        #self.app_charge()
        self.app_battery()
        while True:
            self.app_fire()
            self.app_scroll_text()
            self.app_tetris_ai()
            self.app_race()
            self.app_ble()

GameContext().run()

