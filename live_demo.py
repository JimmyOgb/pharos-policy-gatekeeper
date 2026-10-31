"""Continuous 1080p Playwright video recording script for Pharos Policy Gatekeeper demo.

Records continuous high-definition video of the live web dashboard with
animated cursor, synchronized actions, and merges edge-tts voiceover with ffmpeg.
"""

import asyncio
import os
import shutil
import subprocess
import time
import urllib.request

from playwright.async_api import async_playwright

WORKSPACE = r"C:\Users\NO GO NO\PharosBuild\skills\pharos-policy-gatekeeper"
RAW_VIDEO_DIR = os.path.join(WORKSPACE, "raw_video")
VOICEOVER_PATH = os.path.join(WORKSPACE, "voiceover.mp3")
OUTPUT_MP4 = os.path.join(WORKSPACE, "pharos_policy_gatekeeper_demo.mp4")
DASHBOARD_URL = "http://127.0.0.1:8899"

CURSOR_JS = """
() => {
  if (document.getElementById('demo-cursor')) return;
  const cursor = document.createElement('div');
  cursor.id = 'demo-cursor';
  Object.assign(cursor.style, {
    position: 'fixed', top: '0px', left: '0px',
    width: '24px', height: '24px',
    background: 'rgba(239, 68, 68, 0.85)',
    border: '2px solid white', borderRadius: '50%',
    boxShadow: '0 0 14px rgba(0,0,0,0.6)',
    pointerEvents: 'none', zIndex: '999999',
    transition: 'transform 0.22s cubic-bezier(0.22, 1, 0.36, 1)',
    transform: 'translate(-50%, -50%)'
  });
  document.body.appendChild(cursor);

  document.addEventListener('mousemove', e => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
  });
  document.addEventListener('mousedown', e => {
    cursor.style.transform = 'translate(-50%, -50%) scale(0.65)';
    const ripple = document.createElement('div');
    Object.assign(ripple.style, {
      position: 'fixed', left: e.clientX + 'px', top: e.clientY + 'px',
      width: '12px', height: '12px', borderRadius: '50%',
      border: '2px solid rgba(239, 68, 68, 0.95)',
      transform: 'translate(-50%, -50%) scale(1)',
      opacity: '1', pointerEvents: 'none', zIndex: '999998',
      transition: 'all 0.45s ease-out'
    });
    document.body.appendChild(ripple);
    requestAnimationFrame(() => {
      ripple.style.transform = 'translate(-50%, -50%) scale(4.5)';
      ripple.style.opacity = '0';
    });
    setTimeout(() => ripple.remove(), 450);
  });
  document.addEventListener('mouseup', () => {
    cursor.style.transform = 'translate(-50%, -50%) scale(1)';
  });
}
"""


async def smooth_move(page, target_x: float, target_y: float, steps: int = 25):
    """Smoothly moves the cursor to target coordinates."""
    await page.mouse.move(target_x, target_y, steps=steps)


async def smooth_click(page, selector: str, pause_after: float = 1.5):
    """Moves cursor smoothly to element and clicks with ripple animation."""
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=10000)
    await loc.scroll_into_view_if_needed()
    await asyncio.sleep(0.3)
    box = await loc.bounding_box()
    if box:
        tx = box["x"] + box["width"] / 2
        ty = box["y"] + box["height"] / 2
        await smooth_move(page, tx, ty, steps=30)
        await asyncio.sleep(0.3)
        await page.mouse.click(tx, ty)
    else:
        await loc.click()
    await asyncio.sleep(pause_after)


async def smooth_hover(page, selector: str, pause_duration: float = 2.0):
    """Smoothly moves cursor over an element to draw viewer focus."""
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=10000)
    await loc.scroll_into_view_if_needed()
    box = await loc.bounding_box()
    if box:
        tx = box["x"] + box["width"] / 2
        ty = box["y"] + box["height"] / 2
        await smooth_move(page, tx, ty, steps=25)
    await asyncio.sleep(pause_duration)


async def run_demo():
    print("=== STARTING LIVE DEMO RECORDING ===")

    # Ensure raw video directory is clean
    if os.path.exists(RAW_VIDEO_DIR):
        shutil.rmtree(RAW_VIDEO_DIR)
    os.makedirs(RAW_VIDEO_DIR, exist_ok=True)

    # 1. Start backend server
    print("Starting Policy Gatekeeper backend server...")
    server_cmd = ["python", "cli.py", "serve", "--host", "127.0.0.1", "--port", "8899"]
    server_proc = subprocess.Popen(server_cmd, cwd=WORKSPACE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2.0)

    # Verify server is responding
    try:
        urllib.request.urlopen("http://127.0.0.1:8899/api/status?check_network=false", timeout=3)
        print("Backend server is healthy and ready.")
    except Exception as e:
        print("Error connecting to backend server:", e)
        server_proc.terminate()
        return

    try:
        async with async_playwright() as p:
            print("Launching 1080p Chromium browser with video capture...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=RAW_VIDEO_DIR,
                record_video_size={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            print(f"Navigating to {DASHBOARD_URL}...")
            await page.goto(DASHBOARD_URL, wait_until="networkidle")
            await page.evaluate(CURSOR_JS)
            await asyncio.sleep(2.0)

            # --- SCENE 1: Introduction & Policy Overview (0:00 - 0:42) ---
            print("Recording Scene 1: Header & Active Security Policy Overview...")
            await smooth_hover(page, ".header-brand", pause_duration=4.0)
            await smooth_hover(page, "#badge-network", pause_duration=4.0)
            await smooth_hover(page, ".policy-overview-card", pause_duration=3.0)
            # Hover each of the 3 mini cards
            await smooth_hover(page, ".rule-mini-card:nth-child(1)", pause_duration=5.0)  # Spend limit
            await smooth_hover(page, ".rule-mini-card:nth-child(2)", pause_duration=5.0)  # Allowlist
            await smooth_hover(page, ".rule-mini-card:nth-child(3)", pause_duration=5.0)  # Time window
            await asyncio.sleep(4.0)

            # --- SCENE 2: Authorized Request (ALLOW) (0:42 - 1:08) ---
            print("Recording Scene 2: Authorized Action (ALLOW)...")
            await smooth_click(page, "#preset-allow", pause_after=2.0)
            await smooth_hover(page, "#input-target", pause_duration=3.0)
            await smooth_click(page, "#btn-submit-eval", pause_after=3.0)
            await smooth_hover(page, "#verdict-banner", pause_duration=6.0)
            await smooth_hover(page, "#meta-execution-status", pause_duration=4.0)
            await asyncio.sleep(4.0)

            # --- SCENE 3: Spend Limit Denial Proof (1:08 - 1:32) ---
            print("Recording Scene 3: Denial Proof 1 — Spend Limit Exceeded...")
            await smooth_click(page, "#preset-deny-spend", pause_after=2.0)
            await smooth_hover(page, "#input-value-wei", pause_duration=3.0)
            await smooth_click(page, "#btn-submit-eval", pause_after=3.0)
            await smooth_hover(page, "#verdict-banner", pause_duration=6.0)
            await smooth_hover(page, "#meta-deciding-rule", pause_duration=4.0)
            await asyncio.sleep(4.0)

            # --- SCENE 4: Allowlist Denial Proof (1:32 - 1:50) ---
            print("Recording Scene 4: Denial Proof 2 — Target Not Allowlisted...")
            await smooth_click(page, "#preset-deny-allowlist", pause_after=2.0)
            await smooth_hover(page, "#input-target", pause_duration=2.5)
            await smooth_click(page, "#btn-submit-eval", pause_after=2.5)
            await smooth_hover(page, "#verdict-banner", pause_duration=5.0)
            await asyncio.sleep(4.0)

            # --- SCENE 5: Time Window Denial Proof (1:50 - 2:14) ---
            print("Recording Scene 5: Denial Proof 3 — Outside Time Window...")
            await smooth_click(page, "#preset-deny-time", pause_after=2.0)
            await smooth_hover(page, "#input-timestamp", pause_duration=3.0)
            await smooth_click(page, "#btn-submit-eval", pause_after=3.0)
            await smooth_hover(page, "#verdict-banner", pause_duration=6.0)
            await smooth_hover(page, "#meta-deciding-rule", pause_duration=4.0)
            await asyncio.sleep(4.0)

            # --- SCENE 6: Fail-Closed Boundary Isolation (2:14 - 2:34) ---
            print("Recording Scene 6: Fail-Closed Boundary Proof...")
            await smooth_hover(page, ".rule-traces-container", pause_duration=6.0)
            await smooth_hover(page, ".meta-item:nth-child(4)", pause_duration=6.0)
            await asyncio.sleep(6.0)

            # --- SCENE 7: Audit Ledger & Hash Chain Verification (2:34 - 2:58) ---
            print("Recording Scene 7: Audit Ledger & Cryptographic Hash Verification...")
            await smooth_hover(page, ".audit-card", pause_duration=3.0)
            await page.evaluate("window.scrollBy({ top: 350, behavior: 'smooth' })")
            await asyncio.sleep(2.0)
            await smooth_hover(page, ".audit-table", pause_duration=6.0)
            await smooth_click(page, "#btn-verify-audit", pause_after=3.0)
            await smooth_hover(page, "#integrity-banner", pause_duration=7.0)
            await asyncio.sleep(4.0)

            # --- SCENE 8: Security Disclosure & Summary (2:58 - 3:28) ---
            print("Recording Scene 8: Security Disclosure & Conclusion...")
            await smooth_hover(page, ".audit-footer-note", pause_duration=8.0)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await asyncio.sleep(2.0)
            await smooth_hover(page, ".app-header", pause_duration=12.0)
            await asyncio.sleep(6.0)

            print("Closing browser context to finalize video stream...")
            await context.close()
            await browser.close()

    finally:
        server_proc.terminate()
        server_proc.wait(timeout=3)
        print("Backend server stopped.")

    # 2. Locate recorded .webm
    recorded_files = [f for f in os.listdir(RAW_VIDEO_DIR) if f.endswith(".webm")]
    if not recorded_files:
        print("ERROR: No .webm video file found in raw_video directory!")
        return

    raw_webm = os.path.join(RAW_VIDEO_DIR, recorded_files[0])
    print(f"Recorded raw video: {raw_webm} (Size: {os.path.getsize(raw_webm)} bytes)")

    # 3. Merge audio and video using ffmpeg
    print("Merging raw video and edge-tts narration using ffmpeg...")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", raw_webm,
        "-i", VOICEOVER_PATH,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT_MP4,
    ]

    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg merge error:", res.stderr)
        return

    print("=== VIDEO MERGE COMPLETE ===")
    print(f"Output MP4: {OUTPUT_MP4}")
    print(f"File Size:  {os.path.getsize(OUTPUT_MP4)} bytes")


if __name__ == "__main__":
    asyncio.run(run_demo())
