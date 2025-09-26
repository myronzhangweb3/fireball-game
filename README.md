# Fireball Game

## Project Description

This is an interactive game where players use body movements, detected via MediaPipe Pose, to launch fireballs. The game features both single-player (against an AI) and two-player modes. Players aim to reduce their opponent's health to zero while avoiding incoming fireballs.

## Features

*   **Pose-based Controls**: Utilize MediaPipe for real-time body pose detection to control fireball launching.
*   **Single-Player Mode**: Challenge an AI opponent.
*   **Two-Player Mode**: Compete against another player.
*   **Health System**: Players and AI now have a configurable health bar (default 10 health points).
*   **Enhanced Visuals**: 
    *   Stylized heart shapes for player/AI health indicators.
    *   Distinct, image-based fireballs for Player 1 (red) and Player 2/AI (blue).
*   **Sound Effects**: Immersive sound effects for background music, fireball launches, and hits.
*   **Game Over & Restart**: Clear game over state with an option to restart.

## Installation

### Prerequisites

*   Python 3.12+

### Steps

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/fireball-game.git # Replace with your actual repo URL
    cd fireball-game
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Game

To start the game, run the `main.py` script:

```bash
python main.py
```

Upon launching, you will be prompted to select between "Single Player" and "Two Player" modes.
