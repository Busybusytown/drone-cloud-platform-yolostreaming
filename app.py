# import threading
# import time
# import cv2
# import atexit
# import signal
# import sys
# import os # Added for path checking
#
# from flask import Flask, Response, jsonify
# from detect import YOLOProcessor
# from video_stream import FFmpegStreamer
#
# app = Flask(__name__)
#
# # --- Configuration ---
# VIDEO_SOURCE = "rtmp://localhost:1935/live/dji_stream"
# #VIDEO_SOURCE = r"D:\flask\G1501.mp4" # Use raw string to handle backslashes
# YOLO_MODEL_PATH = 'model/best.pt' # <<--- Configure your model path
# RTMP_PUSH_URL = "rtmp://localhost:1935/live/stream" # <<--- Configure your RTMP push URL
#
# """
# 调整推流参数
# Target frame rate for processing and pushing
# Adjust frame size for processing/pushing (optional, can use original)
# If None, use original source size
# """
# TARGET_FPS = 30
# TARGET_WIDTH = None
# TARGET_HEIGHT = None
#
#
# # --- Global Variables for Stream Management ---
# processor = None
# streamer = None
# stream_thread = None
# stop_event = threading.Event() # Event to signal the thread to stop
#
# # --- Stream Processing Function (Runs in Thread) ---
# def run_stream(processor: YOLOProcessor, streamer: FFmpegStreamer, stop_event: threading.Event):
#     """
#     Main loop for reading frames, processing, and pushing to FFmpeg.
#     Runs in a separate thread.
#     """
#     print("Stream thread started.")
#
#     # --- Check if video source file exists BEFORE opening ---
#     if isinstance(processor.video_source, str) and not processor.video_source.startswith(('rtmp://', 'rtsp://', 'http://', 'https://')) and not os.path.exists(processor.video_source):
#          print(f"Error: Video source file not found at {processor.video_source}")
#          # Generate an error image to push or just exit? Let's just exit the thread.
#          # For robustness, you might push an error stream or image
#          return # Exit the thread if file not found
#
#     # Open video source
#     if not processor.open_video_source():
#         print("Failed to open video source, stream thread exiting.")
#         # Maybe signal an error state somewhere accessible
#         return
#
#     # Get dimensions after opening source
#     # Use target dimensions if specified, otherwise use source dimensions
#     push_width, push_height = processor.get_frame_dimensions()
#     if TARGET_WIDTH is not None and TARGET_HEIGHT is not None:
#         push_width, push_height = TARGET_WIDTH, TARGET_HEIGHT
#
#     # Start FFmpeg streamer
#     # Need to pass the actual dimensions we will push
#     streamer.width = push_width
#     streamer.height = push_height
#     streamer.rtmp_url = RTMP_PUSH_URL # Ensure streamer uses current config
#     if not streamer.start():
#         print("Failed to start FFmpeg streamer, stream thread exiting.")
#         processor.release() # Release video source
#         return
#
#     frame_count = 0
#     start_time = time.time()
#
#     while not stop_event.is_set(): # Loop while stop event is not set
#         frame_read_success, frame = processor.process_next_frame()
#
#         if not frame_read_success or frame is None:
#             # If frame read failed (and wasn't just a loop point in a file that succeeded after reset)
#             # For file sources, process_next_frame already tries to loop.
#             # If it fails *after* trying to loop, it's a persistent read error.
#             print("Failed to get next frame from processor after trying to loop. Stopping stream thread.")
#             stop_event.set() # Signal to stop the loop
#             continue # Exit this iteration
#
#         # Resize frame if target dimensions are specified and different
#         # Ensure frame has 3 dimensions before resizing or pushing
#         if frame is not None:
#              if len(frame.shape) == 2:
#                   frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
#              elif len(frame.shape) == 4: # Handle potential alpha channel if needed
#                   frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
#
#              if (TARGET_WIDTH is not None and TARGET_HEIGHT is not None and
#                  (frame.shape[1] != TARGET_WIDTH or frame.shape[0] != TARGET_HEIGHT)):
#                  resized_frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
#                  frame_to_push = resized_frame
#              else:
#                  # Use original frame dimensions for pushing
#                  frame_to_push = frame
#
#         else: # Should not happen if frame_read_success is True, but good defensive check
#             print("Warning: Frame is None despite read success flag. Skipping frame.")
#             continue
#
#
#         # Write frame to FFmpeg
#         if not streamer.write_frame(frame_to_push):
#             print("Failed to write frame to streamer. FFmpeg process likely exited. Stopping stream thread.")
#             stop_event.set() # Signal to stop the loop
#             continue # Exit this iteration
#
#         frame_count += 1
#
#         # Frame rate control
#         # Basic frame rate control, might need refinement for precision over long runs
#         time_since_start = time.time() - start_time
#         expected_time = frame_count / TARGET_FPS
#         sleep_duration = expected_time - time_since_start
#
#         if sleep_duration > 0:
#              # print(f"Frame {frame_count}: Time since start {time_since_start:.4f}s, Expected time {expected_time:.4f}s, Sleeping for {sleep_duration:.4f}s") # Debug sleep
#              time.sleep(sleep_duration)
#         # else:
#              # print(f"Frame {frame_count}: Running behind schedule. No sleep needed.") # Debug sleep
#
#
#     print("Stream thread loop finished. Cleaning up...")
#     # Cleanup resources when the loop exits
#     processor.release()
#     streamer.stop()
#     print("Stream thread exited.")
#
#
# # --- Flask Routes ---
#
# @app.route("/")
# def index():
#     """Simple status endpoint."""
#     status = "running" if stream_thread and stream_thread.is_alive() else "stopped"
#     streamer_status = "running" if streamer and streamer.is_running() else "stopped"
#     return f"Stream Status: {status}<br>FFmpeg Status: {streamer_status}<br>Access /start-stream or /stop-stream"
#
#
# @app.route("/start-stream", methods=['GET', 'POST'])
# def start_stream_route():
#     """Starts the video processing and streaming thread."""
#     global stream_thread, stop_event, processor, streamer
#
#     if stream_thread and stream_thread.is_alive():
#         return jsonify({"status": "already running", "message": "Stream is already active."}), 200
#
#     print("Starting stream...")
#
#     # Reset stop event
#     stop_event.clear()
#
#     # Initialize components
#     # Ensure dimensions are obtained after opening the video source
#     processor = YOLOProcessor(video_source=VIDEO_SOURCE, model_path=YOLO_MODEL_PATH)
#     # Streamer dimensions will be set in run_stream after processor opens source
#     streamer = FFmpegStreamer(width=1, height=1, rtmp_url=RTMP_PUSH_URL) # Placeholder dimensions
#
#     # Create and start the new thread
#     # Pass processor and streamer instances to the thread function
#     stream_thread = threading.Thread(target=run_stream, args=(processor, streamer, stop_event))
#     stream_thread.daemon = True # Allow main program to exit even if thread is running
#     stream_thread.start()
#
#     return jsonify({"status": "starting", "message": "Attempting to start stream thread."}), 200
#
# @app.route("/stop-stream", methods=['GET', 'POST'])
# def stop_stream_route():
#     """Stops the video processing and streaming thread."""
#     global stream_thread, stop_event, processor, streamer
#
#     if stream_thread and stream_thread.is_alive():
#         print("Stopping stream...")
#         stop_event.set() # Signal the thread to stop
#
#         # Optional: Wait for the thread to finish (can block the request)
#         # stream_thread.join(timeout=10) # Wait up to 10 seconds
#
#         # Check if thread is still alive after join or immediately
#         if stream_thread.is_alive():
#              return jsonify({"status": "stopping", "message": "Signal sent to stop stream thread, but it might take a moment."}), 200
#         else:
#              # Cleanup resources directly if join was used and successful,
#              # or if we are confident the thread has exited right after setting the event
#              # Note: run_stream() also handles this, but explicit cleanup here
#              # can be a fallback or confirmation. Be careful not to call release/stop twice.
#              # processor.release() # run_stream thread handles this
#              # streamer.stop()     # run_stream thread handles this
#              processor, streamer, stream_thread = None, None, None # Clear global references
#              return jsonify({"status": "stopped", "message": "Stream thread has stopped."}), 200
#     else:
#         return jsonify({"status": "not running", "message": "No stream thread is currently active."}), 200
#
# # --- Cleanup on Application Exit ---
# def cleanup_on_exit():
#     """Function to call when the Flask app is shutting down."""
#     print("Flask app shutting down. Stopping stream thread...")
#     global stream_thread, stop_event, processor, streamer
#     if stream_thread and stream_thread.is_alive():
#         stop_event.set() # Signal stop
#         # Give the thread a moment to process the stop signal and clean up itself
#         stream_thread.join(timeout=5)
#         if stream_thread.is_alive():
#             print("Warning: Stream thread did not finish cleanly within timeout.")
#
#     # Final explicit cleanup as a safeguard
#     if processor and processor.cap: # Check if processor exists and cap is open
#         print("Running final processor cleanup...")
#         processor.release()
#         processor = None
#     if streamer and streamer.process and streamer.process.poll() is None: # Check if streamer exists and process is running
#         print("Running final streamer cleanup...")
#         streamer.stop()
#         streamer = None
#
# # Register cleanup function
# atexit.register(cleanup_on_exit)
#
# # Handle signals for graceful shutdown (like Ctrl+C)
# def signal_handler(signum, frame):
#     print(f"\nReceived signal {signum}. Shutting down.")
#     cleanup_on_exit()
#     # sys.exit(0) # Let Flask's runner handle exiting
#
# # signal.signal(signal.SIGINT, signal_handler) # SIGINT is often handled by Flask's reloader
# # signal.signal(signal.SIGTERM, signal_handler) # Handle SIGTERM
#
# # --- Main Entry Point ---
# if __name__ == '__main__':
#     print("Starting Flask application...")
#     # It's generally recommended to disable the reloader when using threads
#     # in Flask development, or use a production WSGI server like Gunicorn
#     # in production which handles multiple processes/workers.
#     app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
#
#
import threading
import time
import cv2
import atexit
import signal
import sys
import os

from flask import Flask, Response, jsonify
from detect import YOLOProcessor
from video_stream import FFmpegStreamer

# 在文件的最上面声明全局变量
global stream_thread, stop_event, processor, streamer

# 初始化 Flask 应用实例
app = Flask(__name__)

# --- 配置 ---
VIDEO_SOURCE = "rtmp://localhost:1935/live/dji_stream"
YOLO_MODEL_PATH = 'model/best.pt'
RTMP_PUSH_URL = "rtmp://localhost:1935/live/stream"
TARGET_FPS = 30
TARGET_WIDTH = None
TARGET_HEIGHT = None


# --- 全局变量 ---
processor = None
streamer = None
stream_thread = None
stop_event = threading.Event() # 用于向后台线程发送停止信号


# --- 流处理函数 (在后台线程中运行) ---
def run_stream(processor: YOLOProcessor, streamer: FFmpegStreamer, stop_event: threading.Event):
    """
    主循环：从视频源读取帧 -> YOLO 检测处理 -> 将处理后的帧写入 FFmpeg 推流管道。
    此函数在独立的后台线程中运行。
    """
    print("Stream thread started.")
    open_delay = 5
    successfully_opened = False

    while not stop_event.is_set():
        print(f"Attempting to open video source: {processor.video_source}")
        if processor.open_video_source():
            print("Video source opened successfully.")
            successfully_opened = True
            break
        else:
            print(f"Failed to open video source. Retrying in {open_delay} seconds...")
            if stop_event.is_set():
                print("Stop event received during open attempt, exiting.")
                return
            time.sleep(open_delay)
            if stop_event.is_set():
                print("Stop event received after retry delay, exiting.")
                return

    if not successfully_opened:
        print("Stream thread exiting because video source could not be opened.")
        return

    print("Video source opened successfully. Proceeding to frame processing.")

    push_width, push_height = processor.get_frame_dimensions()

    if TARGET_WIDTH is not None and TARGET_HEIGHT is not None:
        if TARGET_WIDTH > 0 and TARGET_HEIGHT > 0:
            push_width, push_height = TARGET_WIDTH, TARGET_HEIGHT
        else:
            print(f"Error: Invalid TARGET_WIDTH ({TARGET_WIDTH}) or TARGET_HEIGHT ({TARGET_HEIGHT}). Stream thread exiting.")
            processor.release()
            return
    else:
        if push_width is None or push_height is None:
            print("Error: Could not get original video source dimensions. Stream thread exiting.")
            processor.release()
            return

    streamer.width = push_width
    streamer.height = push_height
    streamer.rtmp_url = RTMP_PUSH_URL
    streamer_started = streamer.start()

    if not streamer_started:
        print("Failed to start FFmpeg streamer after opening video source. Stream thread exiting.")
        processor.release()
        return

    frame_count = 0
    start_time = time.time()

    while not stop_event.is_set():
        frame_read_success, frame = processor.process_next_frame()

        if not frame_read_success or frame is None:
            print("Failed to get next frame from processor. Stream likely ended or has issues. Stopping stream thread.")
            break

        frame_to_push = frame

        if (TARGET_WIDTH is not None and TARGET_HEIGHT is not None and
            (frame.shape[1] != TARGET_WIDTH or frame.shape[0] != TARGET_HEIGHT)):
             if TARGET_WIDTH > 0 and TARGET_HEIGHT > 0:
                 resized_frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
                 frame_to_push = resized_frame
             else:
                  print(f"Error: Invalid TARGET_WIDTH ({TARGET_WIDTH}) or TARGET_HEIGHT ({TARGET_HEIGHT}) encountered during processing. Skipping frame write.")
                  continue

        if not streamer.write_frame(frame_to_push):
            print("Failed to write frame to streamer. FFmpeg process likely exited. Stopping stream thread.")
            break

        frame_count += 1

        time_since_start = time.time() - start_time
        expected_time = frame_count / TARGET_FPS
        sleep_duration = expected_time - time_since_start

        if sleep_duration > 0:
             time.sleep(sleep_duration)

    print("Stream thread loop finished. Cleaning up resources...")
    if processor:
       processor.release()
    if streamer:
       streamer.stop()
    print("Stream thread exited.")


# --- Flask 路由 ---

@app.route("/")
def index():
    """简单的状态检查端点"""
    status = "running" if stream_thread and stream_thread.is_alive() else "stopped"
    streamer_status = "running" if streamer and streamer.is_running() else "stopped"
    return f"Stream Status: {status}<br>FFmpeg Status: {streamer_status}<br>Access /start-stream or /stop-stream"


@app.route("/start-stream", methods=['GET', 'POST'])
def start_stream_route():
    """手动启动视频处理和推流线程。"""
    global stream_thread, stop_event, processor, streamer

    if stream_thread and stream_thread.is_alive():
        return jsonify({"status": "already running", "message": "Stream is already active."}), 200

    print("Starting stream via /start-stream route...")

    stop_event.clear()

    processor = YOLOProcessor(video_source=VIDEO_SOURCE, model_path=YOLO_MODEL_PATH)
    streamer = FFmpegStreamer(width=1, height=1, rtmp_url=RTMP_PUSH_URL)

    stream_thread = threading.Thread(target=run_stream, args=(processor, streamer, stop_event))
    stream_thread.daemon = True
    stream_thread.start()

    return jsonify({"status": "starting", "message": "Attempting to start stream thread."}), 200


@app.route("/stop-stream", methods=['GET', 'POST'])
def stop_stream_route():
    """手动停止视频处理和推流线程。"""
    global stream_thread, stop_event, processor, streamer

    if stream_thread and stream_thread.is_alive():
        print("Stopping stream via /stop-stream route...")
        stop_event.set()

        if stream_thread.is_alive():
            return jsonify({"status": "stopping", "message": "Signal sent to stop stream thread, but it might take a moment or be stuck."}), 200
        else:
            processor, streamer, stream_thread = None, None, None
            return jsonify({"status": "stopped", "message": "Stream thread has stopped."}), 200
    else:
        return jsonify({"status": "not running", "message": "No stream thread is currently active."}), 200


def cleanup_on_exit():
    """在 Flask 应用或 Python 解释器退出时调用，用于停止线程和清理资源。"""
    global stream_thread, stop_event, processor, streamer

    if stream_thread and stream_thread.is_alive():
        print("Sending stop signal to stream thread...")
        stop_event.set()
        stream_thread.join(timeout=5)
        if stream_thread.is_alive():
            print("Warning: Stream thread did not finish cleanly within timeout during cleanup. It may be stuck.")

    if processor and processor.cap and processor.cap.isOpened():
        print("Running final processor cleanup...")
        processor.release()

    if streamer and streamer.process and streamer.process.poll() is None:
        print("Running final streamer cleanup...")
        streamer.stop()

    global_vars_to_clear = ['processor', 'streamer', 'stream_thread']
    for var_name in global_vars_to_clear:
        if var_name in globals() and globals()[var_name] is not None:
            print(f"Clearing global reference: {var_name}")
            globals()[var_name] = None


atexit.register(cleanup_on_exit)


if __name__ == '__main__':


    print("Starting Flask application...")

    stop_event.clear()

    processor = YOLOProcessor(video_source=VIDEO_SOURCE, model_path=YOLO_MODEL_PATH)
    streamer = FFmpegStreamer(width=1, height=1, rtmp_url=RTMP_PUSH_URL)

    stream_thread = threading.Thread(target=run_stream, args=(processor, streamer, stop_event))
    stream_thread.daemon = True
    stream_thread.start()

    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
