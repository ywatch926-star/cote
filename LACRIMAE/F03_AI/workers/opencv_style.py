"""
F03_AI — OpenCV Style Engine
Oversharpening + Oversaturation + Inverse-Square Glow
Single-pass crunchy look applied AFTER interpolation.
"""
import cv2
import numpy as np
from typing import Optional

def apply_crunchy_style(
    frame: np.ndarray,
    sharpen_int: float = 1.2,
    sat_boost: float = 1.1,
    glow_int: float = 0.4,
    glow_small_ksize: int = 25,
    glow_wide_ksize: int = 71,
    highlight_threshold: int = 205,
) -> np.ndarray:
    """
    Apply the crunchy cinematic look in a single pass.
    
    Args:
        frame: BGR uint8 image (H, W, 3)
        sharpen_int: Unsharp mask intensity (1.0 = no sharpen, 1.5 = strong)
        sat_boost: HSV saturation multiplier (1.0 = no boost, 1.3 = strong)
        glow_int: Glow blend intensity (0.0 = no glow, 0.5 = strong)
        glow_small_ksize: Small glow kernel size
        glow_wide_ksize: Wide glow kernel size
        highlight_threshold: Pixel value threshold for glow isolation
    
    Returns:
        Styled BGR uint8 image
    """
    # ─── FILTER A: UNSHARP MASK (Edge Hardening) ─────────────────────
    blur = cv2.GaussianBlur(frame, (9, 9), 10.0)
    sharpened = cv2.addWeighted(
        frame, 1.0 + sharpen_int,
        blur, -sharpen_int,
        0
    )
    
    # ─── FILTER B: OVERSATURATION (HSV Dynamic Remap) ───────────────
    hsv = cv2.cvtColor(sharpened, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = np.clip(s * sat_boost, 0, 255).astype(np.uint8)
    v = np.clip(v * 1.06, 0, 255).astype(np.uint8)  # slight ambient lift
    color_popped = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)
    
    # ─── FILTER C: INVERSE-SQUARE DEEP GLOW ─────────────────────────
    _, highlights = cv2.threshold(
        color_popped, highlight_threshold, 255, cv2.THRESH_TOZERO
    )
    
    glow_layer_small = cv2.GaussianBlur(
        highlights, (glow_small_ksize, glow_small_ksize), 0
    )
    glow_layer_wide = cv2.GaussianBlur(
        highlights, (glow_wide_ksize, glow_wide_ksize), 0
    )
    
    total_glow = cv2.addWeighted(
        glow_layer_small, 0.7,
        glow_layer_wide, 0.3,
        0
    )
    final_master = cv2.addWeighted(
        color_popped, 1.0,
        total_glow, glow_int,
        0
    )
    
    return final_master


def process_video_style(
    input_path: str,
    output_path: str,
    preset_name: str = "default",
    presets: Optional[dict] = None,
) -> str:
    """
    Apply style engine to entire video file frame by frame.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        preset_name: Name of style preset to use
        presets: Optional pre-loaded presets dict
    
    Returns:
        Output path
    """
    if presets is None:
        from .config import load_style_presets
        presets = load_style_presets()
    
    preset = presets.get(preset_name, presets.get("default"))
    
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        styled = apply_crunchy_style(
            frame,
            sharpen_int=preset.sharpen_int,
            sat_boost=preset.sat_boost,
            glow_int=preset.glow_int,
            glow_small_ksize=preset.glow_small_ksize,
            glow_wide_ksize=preset.glow_wide_ksize,
            highlight_threshold=preset.highlight_threshold,
        )
        out.write(styled)
        frame_count += 1
    
    cap.release()
    out.release()
    
    return output_path
