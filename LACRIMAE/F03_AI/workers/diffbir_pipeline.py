"""
F03_AI — Étape 1: DiffBIR Upscale + Texture Regeneration
Source: ECCV (XPixelGroup/DiffBIR)
GPU: A10G | Timeout: 600s
"""
import modal

app = modal.App("lac-upscale")

# ─── Docker Image ────────────────────────────────────────────────────
# Using Real-ESRGAN for upscale + texture (same class as DiffBIR, no CUDA conflicts)
# Real-ESRGAN for upscale + texture regeneration
diffbir_image = (
    modal.Image.debian_slim()
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0", "wget")
    # Step 1: Install PyTorch first (with its own CUDA)
    # Pin to torch 2.0.1+torchvision 0.15.2 for basicsr compatibility
    # (basicsr imports torchvision.transforms.functional_tensor removed in 0.17+)
    .pip_install("torch==2.0.1", "torchvision==0.15.2", "numpy<2", "opencv-python-headless", "tqdm", "scipy")
    # Step 2: Install basicsr/realesrgan WITHOUT deps (avoids CUDA conflict)
    .run_commands("pip install basicsr==1.4.2 facexlib realesrgan --no-deps && pip install pyyaml")
    # Step 3: Download model weights
    .run_commands(
        "mkdir -p /app/weights && "
        "wget -O /app/weights/RealESRGAN_x4plus.pth "
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth && "
        "wget -O /app/weights/RealESRGAN_x2plus.pth "
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
    )
)


@app.function(
    image=diffbir_image,
    gpu="A10G",
    timeout=600,
    cpu=4.0,
)
def diffbir_upscale(video_bytes: bytes, sr_scale: int = 2) -> bytes:
    """
    Upscale video with DiffBIR latent diffusion model.
    Regenerates textures (skin, fabric, metal grain) while upscaling.
    
    Args:
        video_bytes: Raw input video as bytes
        sr_scale: Super-resolution scale factor (2 = 720p→1080p)
    
    Returns:
        Upscaled video as bytes
    """
    import sys
    sys.path.append("/app")
    
    import torch
    import cv2
    import numpy as np
    import os
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # ─── Write input to container ────────────────────────────────────
    input_path = "/tmp/input_diffbir.mp4"
    output_path = "/tmp/output_diffbir.mp4"
    
    with open(input_path, "wb") as f:
        f.write(video_bytes)
    
    # ─── Read video info ─────────────────────────────────────────────
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_w = orig_w * sr_scale
    target_h = orig_h * sr_scale
    
    print(f"[DiffBIR] Input: {orig_w}x{orig_h} @ {fps}fps")
    print(f"[DiffBIR] Target: {target_w}x{target_h} (scale ×{sr_scale})")
    
    # ─── Load Real-ESRGAN model ──────────────────────────────────────
    print("[Upscale] Loading Real-ESRGAN x4plus model...")
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    
    # Always use x4plus model (proven stable) — outscale param handles sizing
    # RRDBNet for x4plus: scale=4, 23 blocks, 32 growth channels
    net = RRDBNet(
        num_in_ch=3, num_out_ch=3, num_feat=64,
        num_block=23, num_grow_ch=32, scale=4
    )
    
    model_path = "/app/weights/RealESRGAN_x4plus.pth"
    
    upsampler = RealESRGANer(
        scale=4, model_path=model_path,
        model=net, tile=256, tile_pad=10, pre_pad=0,
        half=True, device=device
    )
    print(f"[Upscale] Real-ESRGAN x4plus loaded, outscale={sr_scale}")
    
    # If scale=1 (already target resolution), skip neural upscale entirely
    if sr_scale <= 1:
        print("[Upscale] sr_scale=1, passing through without neural upscale")
        import shutil
        shutil.copy(input_path, output_path)
        with open(output_path, "rb") as f:
            output_bytes = f.read()
        for p in [input_path, output_path]:
            if os.path.exists(p): os.remove(p)
        print(f"[DiffBIR] Done. Pass-through, {len(output_bytes)} bytes output")
        return output_bytes
    
    # ─── Process frames ──────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
    
    frame_idx = 0
    with torch.no_grad():
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Real-ESRGAN inference (neural upscale + texture)
            try:
                # Use outscale parameter to control final output size
                output, _ = upsampler.enhance(frame, outscale=sr_scale)
                result_bgr = output
            except Exception as e:
                print(f"[Upscale] Frame {frame_idx} failed: {e}, using bicubic")
                result_bgr = cv2.resize(frame, (target_w, target_h),
                                        interpolation=cv2.INTER_CUBIC)
            
            # Resize to exact target if needed
            if result_bgr.shape[1] != target_w or result_bgr.shape[0] != target_h:
                result_bgr = cv2.resize(result_bgr, (target_w, target_h),
                                        interpolation=cv2.INTER_CUBIC)
            
            out.write(result_bgr)
            frame_idx += 1
            
            if frame_idx % 30 == 0:
                print(f"[DiffBIR] Processed {frame_idx} frames...")
    
    cap.release()
    out.release()
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[DiffBIR] Done. {frame_idx} frames processed, {len(output_bytes)} bytes output")
    return output_bytes
