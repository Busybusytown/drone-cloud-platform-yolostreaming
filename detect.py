import cv2
from ultralytics import YOLOv10
import torch
import os
import time # Added for potential sleep if needed

class YOLOProcessor:
    def __init__(self, video_source="test1.mp4", model_path="yolov10_model/model.pt"):
        self.video_source = video_source
        self.model_path = model_path

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"YOLOProcessor using device: {self.device}")

        try:
            self.model = YOLOv10(self.model_path)
            self.model.to(self.device)
            print(f"YOLO model loaded successfully from {self.model_path}.")
        except Exception as e:
            print(f"Error loading YOLO model from {self.model_path}: {e}")
            self.model = None

        self.cap = None
        self.width = None
        self.height = None

    def open_video_source(self):
        """Opens the video capture source with retry/timeout settings."""
        print(f"Attempting to open video source: {self.video_source}")
        self.cap = cv2.VideoCapture(self.video_source)

        # --- 尝试设置 VideoCapture 属性以提高 RTMP 连接成功率 ---
        # 注意：这些属性的可用性和效果取决于你的 OpenCV 版本以及它底层依赖的 FFmpeg 版本和编译选项
        # 增加打开超时时间（如果支持），单位毫秒
        # cv2.CAP_PROP_OPEN_TIMEOUT_MSEC = 200000 # 尝试设置为 200 秒，看看是否能突破 30 秒限制
        # 如果上面不支持，有些版本可能支持 CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC
        # cv2.CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC = 200000 # 尝试设置为 200 秒

        # 增加网络缓冲区大小（如果支持），单位字节
        # cv2.CAP_PROP_BUFFERSIZE = 1024 * 1024 # 尝试设置为 1MB

        # 设置 RTMP 缓冲区大小（如果支持）
        # cv2.CAP_PROP_RTMP_BUFFER_SIZE = 1024 * 1024 # 尝试设置为 1MB


        # OpenCV 4.x+ 版本可能通过 setProperty 设置 FFmpeg 参数
        # 这种方式更底层，可以尝试设置 FFmpeg 的超时选项
        # 这里的参数名和格式取决于 OpenCV 对 FFmpeg 属性的封装
        # 有些版本可能支持类似 "timeout" 或 "stimeout" 的属性
        # cap.set(cv2.CAP_PROP_XI_BUFFER_SIZE, 1024*1024) # 这是一个示例属性，可能与网络流无关

        # 根据 OpenCV 文档或源码，寻找 RTMP 或网络流相关的 set 属性
        # 例如，对于网络流，有时可以通过添加 FFmpeg 的输入选项到 URL 来设置
        # 例如 "rtmp://host/app/stream?timeout=60" (但这取决于 cv2.VideoCapture 如何解析 URL)
        # 或者通过 CAP_FFMPEG 的一些标志（不常见）

        # 一个通用的提高网络流稳定性的尝试：设置缓冲区和重新连接参数
        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1024*1024) # 尝试设置缓冲区大小
        # cap.set(cv2.CAP_PROP_READ_TIMEOUT, 60000) # 尝试设置读取超时 (毫秒) - 可能不影响打开
        # cap.set(cv2.CAP_PROP_FFMPEG_THREAD_COUNT, 4) # 增加 FFmpeg 线程数


        # 由于具体的属性名和效果因版本而异，最稳妥的方式是尝试那些文档中提到
        # 或在社区讨论中被证明对网络流有效的属性。
        # 我们先尝试一些常见的，如果不行，可能需要查阅你当前 OpenCV 版本的具体文档。

        # 尝试设置打开超时时间 (可能需要较新的 OpenCV 版本)
        # CAP_PROP_OPEN_TIMEOUT_MSEC 属性可能不存在于所有版本
        try:
            # 尝试设置打开超时为 120 秒 (120000 毫秒)
            if hasattr(cv2, 'CAP_PROP_OPEN_TIMEOUT_MSEC'):
                 self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 120000)
                 print("Set CAP_PROP_OPEN_TIMEOUT_MSEC to 120000.")
            elif hasattr(cv2, 'CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC'):
                 self.cap.set(cv2.CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC, 120000)
                 print("Set CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC to 120000.")
            else:
                 print("CAP_PROP_OPEN_TIMEOUT_MSEC or CAP_PROP_RTMP_OPEN_TIMEOUT_MSEC not available in this OpenCV version.")
        except Exception as e:
            print(f"Error setting CAP_PROP_OPEN_TIMEOUT_MSEC/RTMP_OPEN_TIMEOUT_MSEC: {e}")


        # 尝试设置缓冲区大小
        try:
            if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                 self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1024 * 1024) # 1MB buffer
                 print("Set CAP_PROP_BUFFERSIZE to 1MB.")
            else:
                 print("CAP_PROP_BUFFERSIZE not available in this OpenCV version.")
        except Exception as e:
            print(f"Error setting CAP_PROP_BUFFERSIZE: {e}")

        # ----------------------------------------------------------------------


        if not self.cap.isOpened():
            print(f"Error: Could not open video source {self.video_source}")
            self.cap = None # Set to None if failed to open
            return False

        # Get video dimensions (Only if opened successfully)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # 检查尺寸是否有效，有些流打开时可能无法立即获取尺寸，后续 read() 才会确定
        if self.width <= 0 or self.height <= 0:
            print(f"Warning: Initial video source dimensions invalid: {self.width}x{self.height}. Will retry reading frames.")
            # 不在此处返回 False，继续尝试 read()
        else:
            print(f"Video source dimensions detected: {self.width}x{self.height}")

        return True

    # ... (其余方法 process_next_frame, release 保持不变) ...


    def get_frame_dimensions(self):
        """Returns the dimensions of the video source."""
        return self.width, self.height

    def process_next_frame(self):
        """
        Reads the next frame, performs detection, and returns the frame with detections.

        Returns:
            tuple: (ret, frame) where ret is boolean (True if frame read successfully)
                   and frame is the processed image with detections (or None if failed).
        """
        if self.cap is None or not self.cap.isOpened():
            print("Error: Video source not open.")
            return False, None

        ret, frame = self.cap.read()

        if not ret:
            print("Warning: Could not read frame. Attempting to loop or source ended.")
            # Try to loop if it's a file
            if isinstance(self.video_source, str) and (self.video_source.endswith('.mp4') or self.video_source.endswith('.avi')):
                 self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video file
                 ret, frame = self.cap.read()
                 if not ret:
                     print("Error: Failed to read frame after looping.")
                     return False, None # Still failed after looping
            else:
                 # For streams, a read failure might mean the stream ended or is broken
                 print("Error: Failed to read from stream source.")
                 # Consider adding re-connection logic here for streams if needed
                 return False, None # Cannot loop streams easily

        # If frame was read successfully
        if frame is not None and self.model is not None:
            # Perform detection
            # verbose=False to reduce console output
            results = self.model.predict(source=frame, verbose=False)[0]

            # Draw results directly onto the frame
            # The .plot() method from ultralytics already does this
            processed_frame = results.plot() # Returns a numpy array with drawings

            return True, processed_frame # Return success and the drawn frame
        elif frame is not None and self.model is None:
             # If model failed to load, return original frame
             print("Warning: Model not loaded, returning original frame.")
             return True, frame
        else:
            # Frame is None (e.g., after loop failed)
            return False, None


    def release(self):
        """Releases the video capture resource."""
        if self.cap is not None:
            self.cap.release()
            print("Video source released.")
        self.cap = None # Ensure cap is None after release

