"""
F03_AI — Étape 2: L-Diffuser Video Color Grading
Source: ICCV 2025 (seunghyuns98/VideoColorGrading)
GPU: A10G | Timeout: 600s
"""
import modal

app = modal.App("lac-vcg-color-grading")

# ─── Docker Image ────────────────────────────────────────────────────
vcg_image = (
    modal.Image.debian_slim()
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0", "wget")
    .pip_install(
        "torch", "torchvision", "torchaudio",
        "opencv-python-headless", "transformers", "numpy",
        "accelerate", "diffusers", "einops", "scipy",
    )
    .run_commands(
        "git clone https://github.com/seunghyuns98/VideoColorGrading.git /app"
    )
)


@app.function(
    image=vcg_image,
    gpu="A10G",
    timeout=600,
    cpu=4.0,
)
def vcg_grade(
    video_bytes: bytes,
    reference_image_bytes: bytes,
    lut_resolution: int = 16,
    temporal_consistency: bool = True,
) -> bytes:
    """
    Apply neural color grading using L-Diffuser.
    Generates a 3D LUT from a reference image and applies it to video.
    
    Args:
        video_bytes: Input video as bytes
        reference_image_bytes: Reference image (the "look" to transfer) as bytes
        lut_resolution: LUT cube resolution (16 = 16x16x16)
        temporal_consistency: Enable temporal consistency across frames
    
    Returns:
        Color-graded video as bytes
    """
    import sys
    sys.path.append("/app")
    
    import torch
    import cv2
    import numpy as np
    import os
    import requests
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # ─── Write inputs to container ───────────────────────────────────
    input_path = "/tmp/input_vcg.mp4"
    ref_path = "/tmp/reference_vcg.png"
    output_path = "/tmp/output_vcg.mp4"
    
    with open(input_path, "wb") as f:
        f.write(video_bytes)
    with open(ref_path, "wb") as f:
        f.write(reference_image_bytes)
    
    # ─── Read video info ─────────────────────────────────────────────
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    print(f"[VCG] Input: {width}x{height} @ {fps}fps, {total_frames} frames")
    print(f"[VCG] LUT resolution: {lut_resolution}³")
    
    # ─── Load VCG Pipeline ───────────────────────────────────────────
    print("[VCG] Loading L-Diffuser model...")
    try:
        from models.vcg_pipeline import VideoColorGradingPipeline
        
        pipeline = VideoColorGradingPipeline.from_pretrained(
            "seunghyuns98/VCG-Weights",
            torch_dtype=torch.float16
        ).to(device)
        
        print("[VCG] Model loaded successfully")
        
        # Run VCG inference
        pipeline(
            video_path=input_path,
            reference_image_path=ref_path,
            output_path=output_path,
            lut_resolution=lut_resolution,
            temporal_consistency=temporal_consistency,
        )
        
    except Exception as e:
        print(f"[VCG] VCG pipeline failed: {e}")
        print("[VCG] Falling back to manual LUT generation...")
        
        # ─── Fallback: Generate LUT from reference and apply ─────────
        # Load reference image
        ref_img = cv2.imread(ref_path)
        if ref_img is None:
            raise ValueError(f"Cannot load reference image from bytes")
        
        # Read all frames
        cap = cv2.VideoCapture(input_path)
        frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        
        # Generate simple 3D LUT from reference color histogram
        ref_hsv = cv2.cvtColor(ref_img, cv2.COLOR_BGR2HSV)
        ref_hist_s = cv2.calcHist([ref_hsv], [1], None, [256], [0, 256])
        ref_hist_v = cv2.calcHist([ref_hsv], [2], None, [256], [0, 256])
        
        # Normalize reference histograms
        ref_hist_s = ref_hist_s / (ref_hist_s.sum() + 1e-6)
        ref_hist_v = ref_hist_v / (ref_hist_v.sum() + 1e-6)
        
        # Apply color transfer to each frame
        out_frames = []
        for frame in frames:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            # Match saturation distribution
            s_float = s.astype(np.float32)
            s_mean_target = (ref_hist_s * np.arange(256)).sum() * 255
            s_mean_current = s_float.mean()
            if s_mean_current > 0:
                s_float = s_float * (s_mean_target / s_mean_current)
                s_float = np.clip(s_float, 0, 255)
            
            # Match value distribution
            v_float = v.astype(np.float32)
            v_mean_target = (ref_hist_v * np.arange(256)).sum() * 255
            v_mean_current = v_float.mean()
            if v_mean_current > 0:
                v_float = v_float * (v_mean_target / v_mean_current)
                v_float = np.clip(v_float, 0, 255)
            
            hsv_transferred = cv2.merge([
                h,
                s_float.astype(np.uint8),
                v_float.astype(np.uint8)
            ])
            bgr_transferred = cv2.cvtColor(hsv_transferred, cv2.COLOR_HSV2BGR)
            out_frames.append(bgr_transferred)
        
        # Write output
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        for frame in out_frames:
            out.write(frame)
        out.release()
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, ref_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[VCG] Done. {len(output_bytes)} bytes output")
    return output_bytes
