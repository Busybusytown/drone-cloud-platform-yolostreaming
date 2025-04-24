import subprocess
import sys
import time
class FFmpegStreamer:
    def __init__(self, width, height, rtmp_url="rtmp://localhost/live/stream"): # Make URL configurable
        self.width = width
        self.height = height
        self.rtmp_url = rtmp_url
        self.process = None # FFmpeg process handle

    def start(self):
        """Starts the FFmpeg subprocess."""
        if self.process is not None and self.process.poll() is None:
            print("FFmpeg process is already running.")
            return True # Already running

        # --- 修改 FFmpeg 命令参数 ---
        command = [
            "ffmpeg",
            "-y",  # 覆盖输出文件 (如果存在)
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",  # OpenCV 的默认颜色空间 (BGR)
            "-s", f"{self.width}x{self.height}",  # 设置帧大小
            "-r", "30",  # 设置帧率为 30 FPS (与生成帧率一致)
            "-i", "-",  # 输入通过管道传输

            # --- H.264 编码参数 ---
            "-c:v", "libx264",       # 使用 x264 编解码
            "-preset", "medium",   # 快速编解码设置
            "-tune", "zerolatency",  # 低延迟

            "-vf", "format=yuv420p", # <---  YUV420P 像素格式，兼容性更好

            # <--- 添加/修改: 设置 H.264 Profile 和 Level，降低兼容性要求 ---
            # 尝试 Main Profile, Level 3.1，通常兼容性较好
            "-profile:v", "main",
            "-level:v", "3.1",
            # 如果 main 3.1 仍有问题，可以尝试更低的 baseline profile 和 level 3.0
            # "-profile:v", "baseline",
            # "-level:v", "3.0",
            # <---------------------------------------------------------------
            "-g", "90",              # <--- 添加: 设置关键帧间隔 (GOP size) 为 90 帧 (与 HLS 切片时长 3秒 * 30fps 匹配)
            "-f", "flv",  # 设置流格式为 flv
            self.rtmp_url  # 推流地址
        ]
        # ---------------------------

        print(f"Starting FFmpeg process with command: {' '.join(command)}")

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                # stdout=subprocess.PIPE, # Optional: Capture stdout for debugging
                # stderr=subprocess.PIPE # Optional: Capture stderr for debugging
            )
            print("FFmpeg process started.")
            return True
        except FileNotFoundError:
            print("Error: FFmpeg command not found. Make sure FFmpeg is installed and in your PATH.")
            self.process = None # Ensure process is None on failure
            return False
        except Exception as e:
            print(f"Error starting FFmpeg process: {e}")
            self.process = None # Ensure process is None on failure
            return False

    def write_frame(self, frame):
        """
        Writes a frame (numpy array) to the FFmpeg subprocess stdin.
        Returns True if successful, False otherwise.11
        """
        # ... (unchanged) ...
        if self.process is None or self.process.poll() is not None:
            # print("Warning: FFmpeg process is not running or has exited.") # Reduce console spam
            return False # Process is not running
        try:
            # Convert numpy array to bytes (assuming frame is uint8)
            self.process.stdin.write(frame.tobytes())
            # self.process.stdin.flush()
            return True
        except BrokenPipeError:
             print("Error: Broken pipe when writing to FFmpeg. Process likely exited.")
             self.process = None # Mark process as stopped
             return False
        except Exception as e:
            print(f"Error writing frame to FFmpeg: {e}")
            return False


    def stop(self):
       # ... (unchanged) ...
       pass # Keep the rest of the method as is

    def is_running(self):
       # ... (unchanged) ...
       return self.process is not None and self.process.poll() is None