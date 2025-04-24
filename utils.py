# utils.py
import cv2
import base64

def encode_frame_to_base64(frame, quality=50):
    """把图像压缩为JPEG并编码为Base64"""
    success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        return None
    return base64.b64encode(buffer).decode('utf-8')
