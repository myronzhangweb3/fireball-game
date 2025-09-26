import math
import random
import time

import cv2
import mediapipe as mp
import pygame

from .constants import (
    MODEL_COMPLEXITY, HEART_RADIUS, PLAYER_COOLDOWN, AI_MIN_COOLDOWN, AI_MAX_COOLDOWN, ARM_STRAIGHT_ANGLE,
    THRUST_SENSITIVITY, AI_ANIMATION_SPEED, AI_ANIMATION_RANGE, PLAYABLE_AREA_MARGIN,
    SOUND_BACKGROUND, SOUND_FIREBALL, SOUND_FIREBALL_2, SOUND_HIT, SOUND_WIN,
    VOLUME_BACKGROUND, VOLUME_FIREBALL, VOLUME_FIREBALL_2, VOLUME_HIT, VOLUME_WIN, CAMERA_ZOOM, DEFAULT_HEALTH,
    FIREBALL_RADIUS
)
from .fireball import Fireball
from .utils import get_angle, draw_centered_text, zoom_frame, draw_heart


class Game:
    def __init__(self):
        pygame.init()
        self.mp_pose = mp.solutions.pose
        self.pose_player1 = self.mp_pose.Pose(
            model_complexity=MODEL_COMPLEXITY,
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.7
        )
        self.pose_player2 = self.mp_pose.Pose(
            model_complexity=MODEL_COMPLEXITY,
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Cannot open camera.")
            exit()

        self.fireballs = []
        self.player1_cooldown = 0
        self.player2_cooldown = 0
        self.ai_cooldown = 0
        self.game_over_state = False
        self.winner = None

        self.player1_health = DEFAULT_HEALTH
        self.player2_health = DEFAULT_HEALTH
        self.ai_health = DEFAULT_HEALTH
        
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Cannot read frame from camera.")
            exit()
        self.frame_height, self.frame_width, _ = frame.shape

        self.ai_base_pos = (self.frame_width - 100, self.frame_height // 2)
        self.ai_heart_pos = self.ai_base_pos
        self.animation_time = 0

        self.window_name = 'Fireball Game'
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        self.last_wrist_z_p1 = None
        self.last_wrist_z_p2 = None
        self.debug_data_p1 = {}
        self.debug_data_p2 = {}
        self.game_mode = self.show_mode_selection()
        self.paused = False # Added for pause functionality

        # --- 音效加载 ---
        pygame.mixer.music.load(SOUND_BACKGROUND)
        pygame.mixer.music.play(-1)  # -1表示无限循环
        self.fireball_sound = pygame.mixer.Sound(SOUND_FIREBALL)
        self.fireball2_sound = pygame.mixer.Sound(SOUND_FIREBALL_2)
        self.hit_sound = pygame.mixer.Sound(SOUND_HIT)
        self.win_sound = pygame.mixer.Sound(SOUND_WIN)

        # --- 设置音量 ---
        pygame.mixer.music.set_volume(VOLUME_BACKGROUND)
        self.fireball_sound.set_volume(VOLUME_FIREBALL)
        self.fireball2_sound.set_volume(VOLUME_FIREBALL_2)
        self.hit_sound.set_volume(VOLUME_HIT)
        self.win_sound.set_volume(VOLUME_WIN)

    def show_mode_selection(self):
        selection = None
        button_width, button_height = 400, 100
        
        single_player_pos = (
            self.frame_width // 4 - button_width // 2,
            self.frame_height // 2 - button_height // 2
        )
        two_player_pos = (
            self.frame_width * 3 // 4 - button_width // 2,
            self.frame_height // 2 - button_height // 2
        )

        def mouse_callback(event, x, y, flags, param):
            nonlocal selection
            if event == cv2.EVENT_LBUTTONDOWN:
                if single_player_pos[0] < x < single_player_pos[0] + button_width and \
                   single_player_pos[1] < y < single_player_pos[1] + button_height:
                    selection = 'single'
                elif two_player_pos[0] < x < two_player_pos[0] + button_width and \
                     two_player_pos[1] < y < two_player_pos[1] + button_height:
                    selection = 'two'

        cv2.setMouseCallback(self.window_name, mouse_callback)

        while selection is None:
            frame = self.cap.read()[1]
            frame = cv2.flip(frame, 1)
            
            # Single Player Button
            cv2.rectangle(frame, single_player_pos, (single_player_pos[0] + button_width, single_player_pos[1] + button_height), (0, 255, 0), -1)
            cv2.putText(frame, 'Single Player', (single_player_pos[0] + 50, single_player_pos[1] + 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)

            # Two Player Button
            cv2.rectangle(frame, two_player_pos, (two_player_pos[0] + button_width, two_player_pos[1] + button_height), (0, 0, 255), -1)
            cv2.putText(frame, 'Two Player', (two_player_pos[0] + 70, two_player_pos[1] + 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
            
            cv2.imshow(self.window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                exit()
        
        cv2.setMouseCallback(self.window_name, lambda *args: None)
        return selection

    def run(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                continue

            frame = zoom_frame(frame, CAMERA_ZOOM)
            frame = cv2.flip(frame, 1)

            key = cv2.waitKey(5) & 0xFF
            if key == ord(' '): # Spacebar to toggle pause
                self.paused = not self.paused
                if self.paused:
                    pygame.mixer.music.pause()
                else:
                    pygame.mixer.music.unpause()
            elif key == ord('q'):
                break

            if self.game_over_state:
                if key == ord('r'):
                    self.reset_game()
            elif self.paused:
                # Display PAUSED overlay
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (self.frame_width, self.frame_height), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                text = "PAUSED"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_TRIPLEX, 3, 5)[0]
                text_x = (self.frame_width - text_size[0]) // 2
                text_y = (self.frame_height + text_size[1]) // 2
                cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_TRIPLEX, 3, (255, 255, 255), 5)
            else:
                if self.game_mode == 'single':
                    self.run_single_player(frame)
                else:
                    self.run_two_player(frame)

            cv2.imshow(self.window_name, frame)
        
        self.cleanup()

    def run_single_player(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose_player1.process(rgb_frame)

        self.animate_ai()

        player_landmarks = None
        if results.pose_landmarks:
            player_landmarks = results.pose_landmarks
            # self.mp_drawing.draw_landmarks(
            #     frame, player_landmarks, self.mp_pose.POSE_CONNECTIONS,
            #     self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            #     self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
            # )

        if player_landmarks:
            self.handle_player_input(player_landmarks, 'player1')
        else:
            self.debug_data_p1 = {} # Clear debug data if no player

        if not self.game_over_state and player_landmarks:
            self.handle_ai_action(player_landmarks)
            self.check_collisions_single_player(player_landmarks)

        self.update_and_draw_fireballs(frame)
        self.draw_ui_single_player(frame, player_landmarks)
        self.draw_debug_info_single_player(frame)

    def run_two_player(self, frame):
        mid_x = self.frame_width // 2
        
        # Player 1 (Left side)
        frame_p1 = frame[:, :mid_x]
        rgb_frame_p1 = cv2.cvtColor(frame_p1, cv2.COLOR_BGR2RGB)
        results_p1 = self.pose_player1.process(rgb_frame_p1)

        # Player 2 (Right side)
        frame_p2 = frame[:, mid_x:]
        rgb_frame_p2 = cv2.cvtColor(frame_p2, cv2.COLOR_BGR2RGB)
        results_p2 = self.pose_player2.process(rgb_frame_p2)

        player1_landmarks = None
        if results_p1.pose_landmarks:
            player1_landmarks = results_p1.pose_landmarks
            # self.mp_drawing.draw_landmarks(
            #     frame_p1, player1_landmarks, self.mp_pose.POSE_CONNECTIONS,
            #     self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
            #     self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
            # )

        player2_landmarks = None
        if results_p2.pose_landmarks:
            player2_landmarks = results_p2.pose_landmarks
            # self.mp_drawing.draw_landmarks(
            #     frame_p2, player2_landmarks, self.mp_pose.POSE_CONNECTIONS,
            #     self.mp_drawing.DrawingSpec(color=(66, 245, 117), thickness=2, circle_radius=2),
            #     self.mp_drawing.DrawingSpec(color=(230, 66, 245), thickness=2, circle_radius=2)
            # )

        if player1_landmarks:
            self.handle_player_input(player1_landmarks, 'player1')
        else:
            self.debug_data_p1 = {}

        if player2_landmarks:
            self.handle_player_input(player2_landmarks, 'player2', offset_x=mid_x)
        else:
            self.debug_data_p2 = {}

        if not self.game_over_state:
            self.check_collisions_two_player(player1_landmarks, player2_landmarks, mid_x)

        self.update_and_draw_fireballs(frame)
        self.draw_ui_two_player(frame, player1_landmarks, player2_landmarks, mid_x)
        self.draw_debug_info_two_player(frame)

    def animate_ai(self):
        self.animation_time += AI_ANIMATION_SPEED
        v_offset = int(math.sin(self.animation_time) * AI_ANIMATION_RANGE)
        self.ai_heart_pos = (self.ai_base_pos[0], self.ai_base_pos[1] + v_offset)

    def handle_player_input(self, player_landmarks, player, offset_x=0):
        current_time = time.time()
        
        landmarks = player_landmarks.landmark
        
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]

        left_arm_angle = get_angle(left_shoulder, left_elbow, left_wrist)
        right_arm_angle = get_angle(right_shoulder, right_elbow, right_wrist)
        arms_are_straight = left_arm_angle > ARM_STRAIGHT_ANGLE and right_arm_angle > ARM_STRAIGHT_ANGLE

        last_wrist_z = self.last_wrist_z_p1 if player == 'player1' else self.last_wrist_z_p2
        current_wrist_z = (left_wrist.z + right_wrist.z) / 2
        forward_velocity = 0
        if last_wrist_z is not None:
            forward_velocity = last_wrist_z - current_wrist_z
        
        if player == 'player1':
            self.last_wrist_z_p1 = current_wrist_z
        else:
            self.last_wrist_z_p2 = current_wrist_z

        is_thrusting = abs(forward_velocity) >= THRUST_SENSITIVITY

        # --- Calculate Fire Angle for Debugging ---
        player_frame_width = self.frame_width if self.game_mode == 'single' else self.frame_width // 2
        wrist_mid_x = (left_wrist.x + right_wrist.x) / 2
        wrist_mid_y = (left_wrist.y + right_wrist.y) / 2
        elbow_mid_x = (left_elbow.x + right_elbow.x) / 2
        elbow_mid_y = (left_elbow.y + right_elbow.y) / 2

        wrist_pixel_x = wrist_mid_x * player_frame_width + offset_x
        wrist_pixel_y = wrist_mid_y * self.frame_height
        elbow_pixel_x = elbow_mid_x * player_frame_width + offset_x
        elbow_pixel_y = elbow_mid_y * self.frame_height
        
        dir_x = wrist_pixel_x - elbow_pixel_x
        dir_y = wrist_pixel_y - elbow_pixel_y
        magnitude = math.hypot(dir_x, dir_y)
        
        fire_angle_rad = math.atan2(dir_y, dir_x)
        fire_angle_deg = math.degrees(fire_angle_rad)

        debug_data = {
            'L-Angle': left_arm_angle,
            'R-Angle': right_arm_angle,
            'Arms Straight': arms_are_straight,
            'Fwd Velocity': forward_velocity,
            'Thrusting': is_thrusting,
            'Fire Angle': fire_angle_deg,
            'dir_x': dir_x,
            'dir_y': dir_y,
            'magnitude': magnitude
        }

        if player == 'player1':
            self.debug_data_p1 = debug_data
        else:
            self.debug_data_p2 = debug_data

        cooldown = self.player1_cooldown if player == 'player1' else self.player2_cooldown

        if current_time > cooldown:
            if arms_are_straight and is_thrusting:
                if player == 'player1':
                    self.player1_cooldown = current_time + PLAYER_COOLDOWN
                else:
                    self.player2_cooldown = current_time + PLAYER_COOLDOWN

                # --- Direction Check ---
                is_firing_forward = False
                if (player == 'player1' or self.game_mode == 'single') and dir_x > 0: # Player 1/Single Player fires right
                    is_firing_forward = True
                elif player == 'player2' and dir_x < 0: # Player 2 fires left
                    is_firing_forward = True

                is_firing_upwards = True
                if magnitude > 0:
                    norm_dir_y = dir_y / magnitude
                    if norm_dir_y > 0.8: # Corresponds to about 53 degrees downward
                        is_firing_upwards = False

                if is_firing_forward and is_firing_upwards:
                    # --- Fireball Creation ---
                    if magnitude > 0:
                        norm_dir_x = dir_x / magnitude
                        norm_dir_y = dir_y / magnitude
                    else:
                        norm_dir_x, norm_dir_y = 0, -1 # Fallback

                    palm_offset = 30  # pixels
                    start_x = wrist_pixel_x + norm_dir_x * palm_offset
                    start_y = wrist_pixel_y + norm_dir_y * palm_offset

                    target_x = start_x + dir_x * 100
                    target_y = start_y + dir_y * 100

                    self.fireballs.append(Fireball(start_x, start_y, target_x, target_y, player))
                    
                    if player == 'player1':
                        self.fireball_sound.play()
                    else:
                        self.fireball2_sound.play()
                    
                    if player == 'player1':
                        self.last_wrist_z_p1 = None
                    else:
                        self.last_wrist_z_p2 = None
    
    def handle_ai_action(self, player_landmarks):
        current_time = time.time()
        if current_time > self.ai_cooldown:
            self.ai_cooldown = current_time + random.uniform(AI_MIN_COOLDOWN, AI_MAX_COOLDOWN)
            player_heart_pos = self.get_heart_position(player_landmarks.landmark)
            
            ai_start_x = self.ai_heart_pos[0] - 30
            ai_start_y = self.ai_heart_pos[1]
            self.fireballs.append(Fireball(ai_start_x, ai_start_y, player_heart_pos[0], player_heart_pos[1], 'ai'))
            self.fireball2_sound.play()

    def get_heart_position(self, landmarks, offset_x=0, width=None):
        if width is None:
            width = self.frame_width
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        heart_x = (left_shoulder.x + right_shoulder.x) / 2 * width + offset_x
        heart_y = (left_shoulder.y + right_shoulder.y) / 2 * self.frame_height + 30
        return int(heart_x), int(heart_y)

    def update_and_draw_fireballs(self, frame):
        for fireball in self.fireballs[:]:
            fireball.update()
            fireball.draw(frame)
            if not (0 < fireball.x < self.frame_width and 0 < fireball.y < self.frame_height):
                self.fireballs.remove(fireball)

    def check_collisions_single_player(self, player_landmarks):
        player_heart_pos = self.get_heart_position(player_landmarks.landmark)

        for fireball in self.fireballs[:]:
            if fireball.owner == 'ai' and not fireball.hit:
                if math.hypot(fireball.x - player_heart_pos[0], fireball.y - player_heart_pos[1]) < HEART_RADIUS + FIREBALL_RADIUS:
                    self.player1_health -= 1
                    fireball.hit = True
                    self.hit_sound.play()
                    if self.player1_health <= 0:
                        self.game_over_state = True
                        self.winner = 'AI'
                        self.win_sound.play()
                    self.fireballs.remove(fireball)

            elif fireball.owner == 'player1' and not fireball.hit:
                if math.hypot(fireball.x - self.ai_heart_pos[0], fireball.y - self.ai_heart_pos[1]) < HEART_RADIUS + FIREBALL_RADIUS:
                    self.ai_health -= 1
                    fireball.hit = True
                    self.hit_sound.play()
                    if self.ai_health <= 0:
                        self.game_over_state = True
                        self.winner = 'Player'
                        self.win_sound.play()
                    self.fireballs.remove(fireball)

    def check_collisions_two_player(self, player1_landmarks, player2_landmarks, mid_x):
        if not player1_landmarks or not player2_landmarks:
            return

        player1_heart_pos = self.get_heart_position(player1_landmarks.landmark, 0, mid_x)
        player2_heart_pos = self.get_heart_position(player2_landmarks.landmark, mid_x, self.frame_width / 2)

        for fireball in self.fireballs[:]:
            if fireball.owner == 'player1' and not fireball.hit:
                if math.hypot(fireball.x - player2_heart_pos[0], fireball.y - player2_heart_pos[1]) < HEART_RADIUS + FIREBALL_RADIUS:
                    self.player2_health -= 1
                    fireball.hit = True
                    self.hit_sound.play()
                    if self.player2_health <= 0:
                        self.game_over_state = True
                        self.winner = 'Player 1'
                        self.win_sound.play()
                    self.fireballs.remove(fireball)

            elif fireball.owner == 'player2' and not fireball.hit:
                if math.hypot(fireball.x - player1_heart_pos[0], fireball.y - player1_heart_pos[1]) < HEART_RADIUS + FIREBALL_RADIUS:
                    self.player1_health -= 1
                    fireball.hit = True
                    self.hit_sound.play()
                    if self.player1_health <= 0:
                        self.game_over_state = True
                        self.winner = 'Player 2'
                        self.win_sound.play()
                    self.fireballs.remove(fireball)

    def draw_ui_single_player(self, frame, player_landmarks):
        # Draw health bars
        cv2.putText(frame, f"Player Health: {self.player1_health}", (10, self.frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"AI Health: {self.ai_health}", (self.frame_width - 250, self.frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if player_landmarks:
            heart_pos = self.get_heart_position(player_landmarks.landmark)
            draw_heart(frame, heart_pos, HEART_RADIUS // 3, (0, 0, 255))
            draw_centered_text(frame, "Player", heart_pos, HEART_RADIUS * 4)

        draw_heart(frame, self.ai_heart_pos, HEART_RADIUS // 3, (255, 0, 0))
        draw_centered_text(frame, "AI", self.ai_heart_pos, HEART_RADIUS * 4)
        if self.game_over_state:
            text = f"{self.winner} Wins!"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_TRIPLEX, 3, 5)[0]
            text_x = (self.frame_width - text_size[0]) // 2
            text_y = (self.frame_height + text_size[1]) // 2
            cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_TRIPLEX, 3, (0, 255, 0), 5)

            # 添加重新开始游戏的提示
            restart_text = "Press 'r' to restart"
            restart_text_size = cv2.getTextSize(restart_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            restart_text_x = (self.frame_width - restart_text_size[0]) // 2
            restart_text_y = text_y + restart_text_size[1] + 40
            cv2.putText(frame, restart_text, (restart_text_x, restart_text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)


    def reset_game(self):
        self.fireballs = []
        self.player1_cooldown = 0
        self.player2_cooldown = 0
        self.ai_cooldown = 0
        self.game_over_state = False
        self.winner = None
        self.player1_health = DEFAULT_HEALTH
        self.player2_health = DEFAULT_HEALTH
        self.ai_health = DEFAULT_HEALTH
        self.last_wrist_z_p1 = None
        self.last_wrist_z_p2 = None

    def draw_dashed_rect(self, frame, top_left, bottom_right, color, thickness=1, dash_length=10):
        x1, y1 = top_left
        x2, y2 = bottom_right
        # Top line
        for i in range(x1, x2, dash_length * 2):
            cv2.line(frame, (i, y1), (i + dash_length, y1), color, thickness)
        # Bottom line
        for i in range(x1, x2, dash_length * 2):
            cv2.line(frame, (i, y2), (i + dash_length, y2), color, thickness)
        # Left line
        for i in range(y1, y2, dash_length * 2):
            cv2.line(frame, (x1, i), (x1, i + dash_length), color, thickness)
        # Right line
        for i in range(y1, y2, dash_length * 2):
            cv2.line(frame, (x2, i), (x2, i + dash_length), color, thickness)

    def draw_ui_two_player(self, frame, player1_landmarks, player2_landmarks, mid_x):
        # Draw health bars
        cv2.putText(frame, f"Player 1 Health: {self.player1_health}", (10, self.frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Player 2 Health: {self.player2_health}", (self.frame_width - 300, self.frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        margin = PLAYABLE_AREA_MARGIN
        # Player 1 playable area
        p1_top_left = (margin, margin)
        p1_bottom_right = (mid_x - margin, self.frame_height - margin)
        self.draw_dashed_rect(frame, p1_top_left, p1_bottom_right, (255, 255, 255), 2, 15)

        # Player 2 playable area
        p2_top_left = (mid_x + margin, margin)
        p2_bottom_right = (self.frame_width - margin, self.frame_height - margin)
        self.draw_dashed_rect(frame, p2_top_left, p2_bottom_right, (255, 255, 255), 2, 15)

        if player1_landmarks:
            heart_pos = self.get_heart_position(player1_landmarks.landmark, 0, mid_x)
            draw_heart(frame, heart_pos, HEART_RADIUS // 3, (0, 0, 255))
            draw_centered_text(frame, "Player 1", heart_pos, HEART_RADIUS * 4)
            
            # Check if player 1 is out of bounds
            if not (p1_top_left[0] < heart_pos[0] < p1_bottom_right[0] and \
                    p1_top_left[1] < heart_pos[1] < p1_bottom_right[1]):
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (mid_x, self.frame_height), (0, 0, 255), -1)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                cv2.putText(frame, "OUT OF BOUNDS", (p1_top_left[0] + 20, p1_top_left[1] + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)


        if player2_landmarks:
            heart_pos = self.get_heart_position(player2_landmarks.landmark, mid_x, self.frame_width / 2)
            draw_heart(frame, heart_pos, HEART_RADIUS // 3, (255, 0, 0))
            draw_centered_text(frame, "Player 2", heart_pos, HEART_RADIUS * 4)

            # Check if player 2 is out of bounds
            if not (p2_top_left[0] < heart_pos[0] < p2_bottom_right[0] and \
                    p2_top_left[1] < heart_pos[1] < p2_bottom_right[1]):
                overlay = frame.copy()
                cv2.rectangle(overlay, (mid_x, 0), (self.frame_width, self.frame_height), (0, 0, 255), -1)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                cv2.putText(frame, "OUT OF BOUNDS", (p2_top_left[0] + 20, p2_top_left[1] + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)

        if self.game_over_state:
            text = f"{self.winner} Wins!"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_TRIPLEX, 3, 5)[0]
            text_x = (self.frame_width - text_size[0]) // 2
            text_y = (self.frame_height + text_size[1]) // 2
            cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_TRIPLEX, 3, (0, 255, 0), 5)

    def draw_debug_info_single_player(self, frame):
        y_pos = 30
        cv2.putText(frame, "-- DEBUG INFO --", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += 30

        if not self.debug_data_p1:
            cv2.putText(frame, "No player detected", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            return

        # Arm Angles
        l_angle = self.debug_data_p1.get('L-Angle', 0)
        r_angle = self.debug_data_p1.get('R-Angle', 0)
        cv2.putText(frame, f"Arm Angles (L/R): {l_angle:.1f} / {r_angle:.1f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_pos += 25

        # Arms Straight Condition
        arms_straight = self.debug_data_p1.get('Arms Straight', False)
        color = (0, 255, 0) if arms_straight else (0, 0, 255)
        cv2.putText(frame, f"Arms Straight: {'YES' if arms_straight else 'NO'}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_pos += 30

        # Thrust Velocity
        fwd_vel = self.debug_data_p1.get('Fwd Velocity', 0)
        cv2.putText(frame, f"Fwd Velocity: {fwd_vel:.4f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_pos += 25

        # Thrusting Condition
        is_thrusting = self.debug_data_p1.get('Thrusting', False)
        color = (0, 255, 0) if is_thrusting else (0, 0, 255)
        cv2.putText(frame, f"Thrusting: {'YES' if is_thrusting else 'NO'}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_pos += 25

        # Fire Angle
        fire_angle = self.debug_data_p1.get('Fire Angle', 'N/A')
        angle_color = (255, 255, 255)
        if isinstance(fire_angle, float):
            # Change color based on whether the angle is valid for firing
            is_forward = self.debug_data_p1.get('dir_x', 0) > 0
            is_upward = True
            magnitude = self.debug_data_p1.get('magnitude', 0)
            if magnitude > 0:
                if (self.debug_data_p1.get('dir_y', 0) / magnitude) > 0.8:
                    is_upward = False
            if is_forward and is_upward:
                angle_color = (0, 255, 0) # Green for valid
            else:
                angle_color = (0, 0, 255) # Red for invalid
            cv2.putText(frame, f"Fire Angle: {fire_angle:.1f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color, 2)
        else:
            cv2.putText(frame, f"Fire Angle: {fire_angle}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color, 1)

    def draw_debug_info_two_player(self, frame):
        # Player 1 Debug Info (Left)
        y_pos = 30
        cv2.putText(frame, "-- P1 DEBUG --", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += 30

        if not self.debug_data_p1:
            cv2.putText(frame, "No player 1 detected", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        else:
            l_angle = self.debug_data_p1.get('L-Angle', 0)
            r_angle = self.debug_data_p1.get('R-Angle', 0)
            cv2.putText(frame, f"Arm Angles (L/R): {l_angle:.1f} / {r_angle:.1f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_pos += 25

            arms_straight = self.debug_data_p1.get('Arms Straight', False)
            color = (0, 255, 0) if arms_straight else (0, 0, 255)
            cv2.putText(frame, f"Arms Straight: {'YES' if arms_straight else 'NO'}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 30

            fwd_vel = self.debug_data_p1.get('Fwd Velocity', 0)
            cv2.putText(frame, f"Fwd Velocity: {fwd_vel:.4f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_pos += 25

            is_thrusting = self.debug_data_p1.get('Thrusting', False)
            color = (0, 255, 0) if is_thrusting else (0, 0, 255)
            cv2.putText(frame, f"Thrusting: {'YES' if is_thrusting else 'NO'}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 25

            # P1 Fire Angle
            fire_angle_p1 = self.debug_data_p1.get('Fire Angle', 'N/A')
            angle_color_p1 = (255, 255, 255)
            if isinstance(fire_angle_p1, float):
                is_forward = self.debug_data_p1.get('dir_x', 0) > 0
                is_upward = True
                magnitude = self.debug_data_p1.get('magnitude', 0)
                if magnitude > 0:
                    if (self.debug_data_p1.get('dir_y', 0) / magnitude) > 0.8:
                        is_upward = False
                if is_forward and is_upward:
                    angle_color_p1 = (0, 255, 0)
                else:
                    angle_color_p1 = (0, 0, 255)
                cv2.putText(frame, f"Fire Angle: {fire_angle_p1:.1f}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color_p1, 2)
            else:
                cv2.putText(frame, f"Fire Angle: {fire_angle_p1}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color_p1, 1)

        # Player 2 Debug Info (Right)
        y_pos = 30
        x_pos = self.frame_width - 240
        cv2.putText(frame, "-- P2 DEBUG --", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += 30

        if not self.debug_data_p2:
            cv2.putText(frame, "No player 2 detected", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        else:
            l_angle = self.debug_data_p2.get('L-Angle', 0)
            r_angle = self.debug_data_p2.get('R-Angle', 0)
            cv2.putText(frame, f"Arm Angles (L/R): {l_angle:.1f} / {r_angle:.1f}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_pos += 25

            arms_straight = self.debug_data_p2.get('Arms Straight', False)
            color = (0, 255, 0) if arms_straight else (0, 0, 255)
            cv2.putText(frame, f"Arms Straight: {'YES' if arms_straight else 'NO'}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 30

            fwd_vel = self.debug_data_p2.get('Fwd Velocity', 0)
            cv2.putText(frame, f"Fwd Velocity: {fwd_vel:.4f}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_pos += 25

            is_thrusting = self.debug_data_p2.get('Thrusting', False)
            color = (0, 255, 0) if is_thrusting else (0, 0, 255)
            cv2.putText(frame, f"Thrusting: {'YES' if is_thrusting else 'NO'}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 25

            # P2 Fire Angle
            fire_angle_p2 = self.debug_data_p2.get('Fire Angle', 'N/A')
            angle_color_p2 = (255, 255, 255)
            if isinstance(fire_angle_p2, float):
                is_forward = self.debug_data_p2.get('dir_x', 0) < 0 # Player 2 fires left
                is_upward = True
                magnitude = self.debug_data_p2.get('magnitude', 0)
                if magnitude > 0:
                    if (self.debug_data_p2.get('dir_y', 0) / magnitude) > 0.8:
                        is_upward = False
                if is_forward and is_upward:
                    angle_color_p2 = (0, 255, 0)
                else:
                    angle_color_p2 = (0, 0, 255)
                cv2.putText(frame, f"Fire Angle: {fire_angle_p2:.1f}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color_p2, 2)
            else:
                cv2.putText(frame, f"Fire Angle: {fire_angle_p2}", (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, angle_color_p2, 1)
    def cleanup(self):
        self.pose_player1.close()
        self.pose_player2.close()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    game = Game()
    game.run()
