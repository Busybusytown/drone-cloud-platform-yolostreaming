#     drone-cloud-platform-yolostreaming——Flask后端
这是一个用于实时处理RTMP视频流的后端，主要有拉流、使用yolov10进行目标检测，推流三个功能

使用的RTMP服务器是[nginx-rtmp-win32](https://github.com/illuspas/nginx-rtmp-win32)
## app.py
**功能:** 项目入口与Flask 应用核心。
- 初始化 Flask 实例和路由。
- 提供 /start-stream 和 /stop-stream 路由来启动和停止视频流处理。
- 启动视频流处理线程，该线程将从视频源读取数据、进行 YOLO 目标检测并通过 FFmpeg 推流。
## detect.py
**功能:**
- 加载 YOLOv10 模型。
- 处理视频源的帧，执行目标检测并返回处理后的帧。
## video_stream.py
**功能:**
-启动 FFmpeg 进程并将视频帧写入该进程的输入流。
-将处理后的帧推送到指定的 RTMP 地址。

## 如何配置：
修改 app.py 中的配置项：
- VIDEO_SOURCE: 配置视频源的 RTMP 地址或本地文件路径。
- YOLO_MODEL_PATH: 配置目标检测模型的路径。
- RTMP_PUSH_URL: 配置视频推流的目标 RTMP 地址。

**安装依赖**

···
pip install -r requirements.txt
···
