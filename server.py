#!/usr/bin/env python3
"""
文本转语音在线工具 - 本地服务器
提供静态文件服务 + Edge TTS API 代理
用法: python server.py
依赖: pip install edge-tts
"""

import asyncio
import io
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import edge_tts
except ImportError:
    print("错误：缺少 edge-tts 依赖包")
    print("请运行: pip install edge-tts")
    sys.exit(1)


class TTSHandler(SimpleHTTPRequestHandler):
    """处理静态文件和 TTS API 请求"""

    def do_POST(self):
        if self.path == "/api/tts":
            self._handle_tts()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def end_headers(self):
        self._set_cors_headers()
        super().end_headers()

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _handle_tts(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            text = data.get("text", "").strip()
            voice = data.get("voice", "zh-CN-XiaoxiaoNeural")
            rate = data.get("rate", "+0%")
            pitch = data.get("pitch", "+0Hz")

            if not text:
                self._send_json_error(400, "文本内容不能为空")
                return

            # 调用 edge-tts 合成语音
            audio_data = asyncio.run(self._synthesize(text, voice, rate, pitch))

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio_data)))
            self.end_headers()
            self.wfile.write(audio_data)

        except json.JSONDecodeError:
            self._send_json_error(400, "请求格式错误")
        except Exception as e:
            print(f"TTS 合成错误: {e}")
            self._send_json_error(500, f"语音合成失败: {e}")

    async def _synthesize(self, text, voice, rate, pitch):
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    def _send_json_error(self, code, message):
        response = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        # 简化日志输出
        if self.path.startswith("/api/"):
            print(f"[API] {self.command} {self.path} - {args[1] if len(args) > 1 else ''}")
        elif not self.path.endswith((".css", ".js", ".ico", ".png", ".jpg")):
            super().log_message(format, *args)


def main():
    host = "0.0.0.0"
    port = 8000

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效的端口号: {sys.argv[1]}")
            sys.exit(1)

    # 切换到脚本所在目录（确保静态文件可访问）
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    server = HTTPServer((host, port), TTSHandler)
    print(f"文本转语音服务已启动")
    print(f"访问地址: http://localhost:{port}")
    print(f"按 Ctrl+C 停止服务")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
