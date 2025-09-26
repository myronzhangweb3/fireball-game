import math
import cv2
import numpy as np

from .constants import FIREBALL_RADIUS, FIREBALL_SPEED, FIREBALL_IMAGE_RED, FIREBALL_IMAGE_BLUE

class Fireball:
    """Represents a single fireball in the game."""
    def __init__(self, x, y, target_x, target_y, owner):
        self.x = x
        self.y = y
        self.owner = owner
        self.hit = False
        self.radius = FIREBALL_RADIUS
        self.trail = []

        if owner == 'player1':
            self.image = cv2.imread(FIREBALL_IMAGE_RED, cv2.IMREAD_UNCHANGED)
        elif owner == 'player2' or owner == 'ai':
            self.image = cv2.imread(FIREBALL_IMAGE_BLUE, cv2.IMREAD_UNCHANGED)
        
        if self.image is None:
            print(f"Error: Could not load fireball image for {owner}")
            # Fallback to drawing circles if image not found
            self.draw_fallback = True
            if owner == 'player1':
                self.color = (0, 165, 255)
            elif owner == 'player2':
                self.color = (255, 0, 255)
            else: # AI
                self.color = (255, 0, 255)
        else:
            self.draw_fallback = False
            self.image = cv2.resize(self.image, (self.radius * 2, self.radius * 2))

        angle = math.atan2(target_y - y, target_x - x)
        self.dx = math.cos(angle) * FIREBALL_SPEED
        self.dy = math.sin(angle) * FIREBALL_SPEED

    def update(self):
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > 10:
            self.trail.pop(0)
        self.x += self.dx
        self.y += self.dy

    def draw(self, frame):
        if self.draw_fallback:
            # Fallback drawing (old circle method)
            for i, pos in enumerate(self.trail):
                alpha = (i + 1) / len(self.trail)
                overlay = frame.copy()
                cv2.circle(overlay, pos, self.radius // 2, self.color, -1)
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            border_color = (0, 255, 255) if self.owner.startswith('player') else (255, 255, 0)
            cv2.circle(frame, (int(self.x), int(self.y)), self.radius, self.color, -1)
            cv2.circle(frame, (int(self.x), int(self.y)), self.radius, border_color, 2)
        else:
            # Draw image
            x_offset = int(self.x - self.radius)
            y_offset = int(self.y - self.radius)

            # Ensure the fireball is within frame boundaries
            y1, y2 = max(0, y_offset), min(frame.shape[0], y_offset + self.image.shape[0])
            x1, x2 = max(0, x_offset), min(frame.shape[1], x_offset + self.image.shape[1])

            # Calculate the region of the image to paste
            img_y1, img_y2 = y1 - y_offset, y2 - y_offset
            img_x1, img_x2 = x1 - x_offset, x2 - x_offset

            if img_x1 < img_x2 and img_y1 < img_y2:
                # Extract the alpha channel and invert it for the background mask
                alpha_s = self.image[img_y1:img_y2, img_x1:img_x2, 3] / 255.0
                alpha_l = 1.0 - alpha_s

                # Extract the color channels of the fireball image
                for c in range(0, 3):
                    frame[y1:y2, x1:x2, c] = (alpha_s * self.image[img_y1:img_y2, img_x1:img_x2, c] + \
                                              alpha_l * frame[y1:y2, x1:x2, c])
