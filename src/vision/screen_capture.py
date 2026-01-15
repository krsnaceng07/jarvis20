
import asyncio
import mss
import mss.tools
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class ScreenCapture:
    def __init__(self):
        self._streaming = False
        self._sct = mss.mss()
        self._monitor = self._sct.monitors[1]  # Primary monitor
        
    async def start_capture(self, interval=1.0):
        """
        Yields screen frames at the specified interval (in seconds).
        """
        self._streaming = True
        logger.info(f"👀 Vision Started: Capturing screen every {interval}s")
        
        while self._streaming:
            try:
                # Capture the screen
                sct_img = self._sct.grab(self._monitor)
                
                # Resizing and Encoding in Executor to prevent blocking
                loop = asyncio.get_running_loop()
                frame_bytes = await loop.run_in_executor(None, self._process_image, sct_img)
                
                yield frame_bytes
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"❌ Screen Capture Error: {e}")
                await asyncio.sleep(interval) # Prevent rapid loop on error

    def _process_image(self, sct_img):
        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Improved Resizing: Use LANCZOS for better text readability
        img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes (Higher Quality for Text)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85)
        return img_byte_arr.getvalue()

    def stop_capture(self):
        self._streaming = False
        logger.info("🙈 Vision Stopped.")
