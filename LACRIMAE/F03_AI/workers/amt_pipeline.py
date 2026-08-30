"""
F03_AI — Étape 3: AMT-G Frame Interpolation + OpenCV Crunch
Source: CVPR 2023 (MCG-NKU/AMT)
GPU: A10G | Timeout: 900s
Pure tensor — no FFmpeg.
"""
import modal
import cv2
import numpy as np

app = modal.App("lac-amt-interpolation")

# ─── Docker Image ────────────────────────────────────────────────────
amt_image = (
    modal.Image.debian_slim()
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0", "wget")
    .pip_install(
        "torch", "torchvision", "opencv-python-headless",
        "numpy", "tqdm", "einops", "scipy",
    )
    .run_commands(
        "git clone https://github.com/MCG-NKU/AMT.git /app"
    )
    .run_commands(
        "mkdir -p /app/ckpt && "
        "wget -O /app/ckpt/amt-g.pth "
        "https://huggingface.co/lalala125/AMT/resolve/main/amt-g.pth"
    )
)


@app.function(
    image=amt_image,
    gpu="A10G",
    timeout=900,
    cpu=4.0,
)
def amt_interpolate(
    video_bytes: bytes,
    multiplier: int = 4,
    style_preset: str = "default",
) -> bytes:
    """
    Interpolate video to higher FPS using AMT-G pure tensor inference.
    Applies OpenCV crunchy style AFTER interpolation.
    
    Args:
        video_bytes: Input video as bytes (30fps)
        multiplier: FPS multiplier (4 = 30fps → 120fps)
        style_preset: Style preset name (default/demon/cinema/crunchy)
    
    Returns:
        Interpolated + styled video as bytes
    """
    import sys
    sys.path.append("/app")
    
    import torch
    import cv2
    import numpy as np
    import os
    from pathlib import Path
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # ─── Write input to container ────────────────────────────────────
    input_path = "/tmp/input_amt.mp4"
    output_path = "/tmp/output_amt.mp4"
    
    with open(input_path, "wb") as f:
        f.write(video_bytes)
    
    # ─── Read video info ─────────────────────────────────────────────
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_fps = int(fps * multiplier)
    
    print(f"[AMT] Input: {width}x{height} @ {fps}fps")
    print(f"[AMT] Target: {target_fps}fps (×{multiplier})")
    print(f"[AMT] Style preset: {style_preset}")
    
    # ─── Load AMT-G Model ───────────────────────────────────────────
    print("[AMT] Loading AMT-G model...")
    try:
        from utils.config import dict2object
        from utils.vfi_utils import build_vfi_model
        
        model_cfg = dict2object({
            'name': 'AMT-G',
            'ckpt': '/app/ckpt/amt-g.pth',
            'flownet': 'VGG',
            'corr_radius': 4,
        })
        model = build_vfi_model(model_cfg).to(device)
        model.eval()
        print("[AMT] AMT-G model loaded")
    except Exception as e:
        print(f"[AMT] AMT-G load failed: {e}, falling back to basic interpolation")
        model = None
    
    # ─── Load style presets ──────────────────────────────────────────
    # Style params (hardcoded defaults, can be loaded from JSON in production)
    style_params = {
        "default": {"sharpen_int": 1.2, "sat_boost": 1.1, "glow_int": 0.4},
        "demon": {"sharpen_int": 1.8, "sat_boost": 1.4, "glow_int": 0.6},
        "cinema": {"sharpen_int": 0.8, "sat_boost": 1.05, "glow_int": 0.3},
        "crunchy": {"sharpen_int": 1.5, "sat_boost": 1.3, "glow_int": 0.5},
    }
    style = style_params.get(style_preset, style_params["default"])
    
    # ─── Extract all frames to memory ────────────────────────────────
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        img_tensor = torch.from_numpy(frame).permute(2, 0, 1).float().to(device) / 255.0
        frames.append(img_tensor)
    cap.release()
    
    print(f"[AMT] Loaded {len(frames)} frames")
    
    # ─── Interpolation Loop ──────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, target_fps, (width, height))
    
    frame_count = 0
    with torch.no_grad():
        for i in range(len(frames) - 1):
            frame0 = frames[i].unsqueeze(0)
            frame1 = frames[i + 1].unsqueeze(0)
            
            # Write original frame anchor
            orig = (frames[i].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
            orig_bgr = cv2.cvtColor(orig, cv2.COLOR_RGB2BGR)
            orig_styled = _apply_style(orig_bgr, style)
            out.write(orig_styled)
            frame_count += 1
            
            # Generate intermediate frames
            for t_step in range(1, multiplier):
                t = t_step / multiplier
                
                if model is not None:
                    try:
                        interp = model.inference(frame0, frame1, t)
                    except Exception:
                        # Fallback: simple linear blend
                        interp = frame0 * (1 - t) + frame1 * t
                else:
                    interp = frame0 * (1 - t) + frame1 * t
                
                out_img = interp.squeeze(0).permute(1, 2, 0).clip(0, 1).cpu().numpy()
                out_bgr = cv2.cvtColor((out_img * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                out_styled = _apply_style(out_bgr, style)
                out.write(out_styled)
                frame_count += 1
        
        # Write final anchor
        if frames:
            final = (frames[-1].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
            final_bgr = cv2.cvtColor(final, cv2.COLOR_RGB2BGR)
            final_styled = _apply_style(final_bgr, style)
            out.write(final_styled)
            frame_count += 1
    
    out.release()
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[AMT] Done. {frame_count} frames output ({target_fps}fps)")
    return output_bytes


def _apply_style(frame: np.ndarray, style: dict) -> np.ndarray:
    """
    Apply OpenCV crunchy style to a single frame.
    Inlined here to avoid import issues in Modal container.
    """
    sharpen_int = style["sharpen_int"]
    sat_boost = style["sat_boost"]
    glow_int = style["glow_int"]
    
    # Unsharp mask
    blur = cv2.GaussianBlur(frame, (9, 9), 10.0)
    sharpened = cv2.addWeighted(frame, 1.0 + sharpen_int, blur, -sharpen_int, 0)
    
    # Saturation boost
    hsv = cv2.cvtColor(sharpened, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = np.clip(s * sat_boost, 0, 255).astype(np.uint8)
    v = np.clip(v * 1.06, 0, 255).astype(np.uint8)
    color_popped = cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)
    
    # Glow
    _, highlights = cv2.threshold(color_popped, 205, 255, cv2.THRESH_TOZERO)
    glow_small = cv2.GaussianBlur(highlights, (25, 25), 0)
    glow_wide = cv2.GaussianBlur(highlights, (71, 71), 0)
    total_glow = cv2.addWeighted(glow_small, 0.7, glow_wide, 0.3, 0)
    final = cv2.addWeighted(color_popped, 1.0, total_glow, glow_int, 0)
    
    return final
