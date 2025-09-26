import math
import cv2
import numpy as np

def draw_heart(frame, center, size, color):
    """Draws a heart shape on the frame."""
    x, y = center
    points = []
    for i in range(0, 628, 5):
        t = i / 100.0
        px = x + size * (16 * math.sin(t) ** 3)
        py = y - size * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((int(px), int(py)))
    
    pts = np.array(points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(frame, [pts], color)

def get_angle(p1, p2, p3):
    angle = math.degrees(math.atan2(p3.y - p2.y, p3.x - p2.x) -
                         math.atan2(p1.y - p2.y, p1.x - p2.x))
    return abs(angle)

def draw_dashed_rect(frame, top_left, bottom_right, color, thickness=1, dash_length=10):
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

def draw_centered_text(frame, text, center, size):
    """
    Draws text centered inside a shape, adapting the font size.
    """
    font_thickness = 2
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Find an optimal font scale
    font_scale = 1.0
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)

    # Reduce font scale until text fits within the shape
    while text_width > size * 1.8: # Use 1.8 for padding
        font_scale *= 0.9
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)

    # Calculate position to center the text
    text_x = int(center[0] - text_width / 2)
    text_y = int(center[1] + text_height / 2)

    cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), font_thickness)

def zoom_frame(frame, zoom_factor):
    if zoom_factor <= 1.0:
        return frame

    h, w, _ = frame.shape

    # New dimensions after zoom
    new_w = int(w / zoom_factor)
    new_h = int(h / zoom_factor)

    # Top-left corner of the crop
    x = (w - new_w) // 2
    y = (h - new_h) // 2

    # Crop the center of the frame
    cropped_frame = frame[y:y + new_h, x:x + new_w]

    # Resize back to original dimensions
    zoomed_frame = cv2.resize(cropped_frame, (w, h), interpolation=cv2.INTER_LINEAR)

    return zoomed_frame
