# =============================================================================
# --- 游戏配置 (可在此处调整游戏参数) ---
# =============================================================================

# --- 性能与精度 ---
MODEL_COMPLEXITY = 0        # 模型复杂度: 0=最快, 1=均衡, 2=最准。降低此值可显著减少延迟。

# --- 尺寸大小 (单位: 像素) ---
HEART_RADIUS = 15       # 心脏的半径 (用于显示和碰撞检测)
FIREBALL_RADIUS = 50    # 火球的半径

# --- 游戏性 ---
FIREBALL_SPEED = 50         # 火球飞行速度 (值越大, 速度越快)
DEFAULT_HEALTH = 2         # 默认生命值
PLAYER_COOLDOWN = 0.5       # 玩家发射火球后的冷却时间 (秒)
AI_MIN_COOLDOWN = 1.5       # AI发射火球的最小间隔时间 (秒)
AI_MAX_COOLDOWN = 2.5       # AI发射火球的最大间隔时间 (秒)

# --- 手势检测灵敏度 ---
ARM_STRAIGHT_ANGLE = 100    # 判定为“手臂伸直”的最小角度 (180为完全伸直)
THRUST_SENSITIVITY = 0.02   # 向前推射动作的灵敏度 (值越大, 要求推得越快)

# --- AI 行为 ---
AI_ANIMATION_SPEED = 0.1    # AI上下移动动画的速度 (值越大, 移动越快)
AI_ANIMATION_RANGE = 80     # AI上下移动的范围 (像素)

# --- 游戏区域 ---
PLAYABLE_AREA_MARGIN = 30 # 玩家可移动区域与屏幕边缘的距离

# --- 音效 ---
SOUND_BACKGROUND = "game/assets/sounds/background.mp3"
SOUND_FIREBALL = "game/assets/sounds/fireball.mp3"
SOUND_FIREBALL_2 = "game/assets/sounds/fireball2.mp3"
SOUND_HIT = "game/assets/sounds/hit.mp3"
SOUND_WIN = "game/assets/sounds/win.mp3"
FIREBALL_IMAGE_RED = "game/assets/fireball_red.png"
FIREBALL_IMAGE_BLUE = "game/assets/fireball_blue.png"

# --- 音量 ---
VOLUME_BACKGROUND = 0.3 # 背景音乐音量
VOLUME_FIREBALL = 0.7   # 火球音效音量
VOLUME_FIREBALL_2 = 1.0 # 第二种火球音效音量
VOLUME_HIT = 0.8        # 击中音效音量
VOLUME_WIN = 1.0        # 胜利音效音量

# --- 摄像头 ---
CAMERA_ZOOM = 1.0 # 摄像头画面缩放比例 (1.0为不缩放, >1.0为放大)
