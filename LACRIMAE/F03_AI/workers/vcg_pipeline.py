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
    
    # ─── BGR/RGB diagnostic probe (from other agent suggestion) ──────
    def check_color_channels(image_matrix, step_name):
        """Analyze raw pixel data to detect BGR/RGB inversion."""
        if hasattr(image_matrix, "detach"):
            img_np = image_matrix.detach().cpu().numpy()
            if img_np.ndim == 4: img_np = img_np[0]
            if img_np.shape[0] == 3:
                img_np = np.transpose(img_np, (1, 2, 0))
            img_np = (img_np * 255).astype(np.uint8)
        else:
            img_np = image_matrix.copy()

        mean_ch0 = float(np.mean(img_np[:, :, 0]))
        mean_ch2 = float(np.mean(img_np[:, :, 2]))

        print(f"\n[COLOR-PROBE] {step_name}")
        print(f"  Canal 0 (B in BGR): {mean_ch0:.2f}")
        print(f"  Canal 2 (R in BGR): {mean_ch2:.2f}")

        if mean_ch0 > mean_ch2 + 20:
            print(f"  🚨 INVERSION BGR/RGB DETECTEE a l'etape '{step_name}'!")
            print(f"  Canal 0 > Canal 2 de {mean_ch0 - mean_ch2:.2f} -> Peau sera BLEUE")
            return True
        elif mean_ch2 > mean_ch0 + 20:
            print(f"  ✅ Format CORRECT (R > B = peau humaine normale)")
            return False
        else:
            print(f"  ⚠️ Canaux proches (pas d'inversion evidente)")
            return False
    
    # ─── Write inputs to container ───────────────────────────────────
    input_path = "/tmp/input_vcg.mp4"
    ref_path = "/tmp/reference_vcg.png"
    output_path = "/tmp/output_vcg.mp4"
    
    with open(input_path, "wb") as f:
        f.write(video_bytes)
    with open(ref_path, "wb") as f:
        f.write(reference_image_bytes)
    
    # ─── PROBE 1: Read first frame from input ────────────────────────
    print("\n" + "="*50)
    print("[COLOR-PROBE] ETAPE 1: Lecture frame brute (OpenCV)")
    print("="*50)
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, first_frame = cap.read()
    cap.release()
    
    if ret:
        check_color_channels(first_frame, "ENTREE_VCG (apres cv2.VideoCapture)")
    
    print(f"[VCG] Input: {width}x{height} @ {fps}fps, {total_frames} frames")
    print(f"[VCG] LUT resolution: {lut_resolution}³")
    
    # ─── Load VCG Pipeline ───────────────────────────────────────────
    print("[VCG] Loading L-Diffuser model...")
    vcg_success = False
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
        vcg_success = True
        
        # ─── PROBE 2: Check VCG output ───────────────────────────────
        print("\n" + "="*50)
        print("[COLOR-PROBE] ETAPE 2: Sortie VCG pipeline")
        print("="*50)
        cap = cv2.VideoCapture(output_path)
        ret, vcg_frame = cap.read()
        cap.release()
        if ret:
            check_color_channels(vcg_frame, "SORTIE_VCG (apres pipeline IA)")
        
    except Exception as e:
        print(f"[VCG] VCG pipeline failed: {e}")
    
    if not vcg_success:
        print("[VCG] Falling back to cinematic grade...")
        
        # ─── Fallback: Simple cinematic color grading ─────────────
        def cinematic_grade(frame, sat_boost=0.8, contrast=1.03, warmth=1.0):
            """Apply subtle cinematic look without destroying skin tones."""
            # 1. Boost saturation slightly (HSV)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_boost, 0, 255)
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
            # 2. Slight contrast boost
            frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=0)
            
            # 3. Warm tone: boost red channel slightly, reduce blue
            frame = frame.astype(np.float32)
            frame[:, :, 2] = np.clip(frame[:, :, 2] * warmth, 0, 255)  # R
            frame[:, :, 0] = np.clip(frame[:, :, 0] / warmth, 0, 255)  # B
            
            return frame.astype(np.uint8)
        
        # Read all frames, apply cinematic grading
        cap = cv2.VideoCapture(input_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # ─── PROBE: Check each frame before write ─────────────
            if frame_count == 0:
                check_color_channels(frame, "FALLBACK_ENTREE (avant cinematic_grade)")
            
            graded = cinematic_grade(frame)
            
            if frame_count == 0:
                check_color_channels(graded, "FALLBACK_SORTIE (apres cinematic_grade)")
            
            out.write(graded)
            frame_count += 1
        
        cap.release()
        out.release()
        print(f"[VCG] Cinematic fallback applied to {frame_count} frames")
        
        # ─── PROBE 3: Check final output file ─────────────────────
        print("\n" + "="*50)
        print("[COLOR-PROBE] ETAPE 3: Verification fichier final")
        print("="*50)
        cap = cv2.VideoCapture(output_path)
        ret, final_frame = cap.read()
        cap.release()
        if ret:
            check_color_channels(final_frame, "FICHIER_FINAL (relu depuis output.mp4)")
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, ref_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[VCG] Done. {len(output_bytes)} bytes output")
    return output_bytes
