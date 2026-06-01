import whisper
import os

# ✅ 关键：把你的 ffmpeg 路径加入 PATH（无需管理员权限）
os.environ["PATH"] = r"C:\Users\irisgao\Documents\ocr\ffmpeg-8.1.1-essentials_build\ffmpeg-8.1.1-essentials_build\bin;" + os.environ["PATH"]

# ✅ 输入和输出路径
mp3_path = r"C:\Users\irisgao\Documents\ocr\3.mp3"
lrc_path = r"C:\Users\irisgao\Documents\ocr\3.lrc"

def format_time(seconds):
    """把秒转成 LRC 时间格式 [mm:ss.xx]"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    millisec = int((seconds - int(seconds)) * 100)
    return f"[{minutes:02d}:{secs:02d}.{millisec:02d}]"

def mp3_to_lrc(mp3_path, lrc_path):
    print("✅ 正在加载 Whisper 模型...")
    model = whisper.load_model("medium")  # medium 对口音识别更准确

    print("✅ 正在识别音频...")
    result = model.transcribe(mp3_path, language="en", task="transcribe")

    segments = result["segments"]

    print("✅ 正在生成 LRC 文件...")
    with open(lrc_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start_time = seg["start"]
            text = seg["text"].strip()

            time_tag = format_time(start_time)
            f.write(f"{time_tag}{text}\n")

    print(f"✅ 完成！LRC 文件已生成：{lrc_path}")

if __name__ == "__main__":
    mp3_to_lrc(mp3_path, lrc_path)
