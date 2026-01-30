import asyncio
import edge_tts
from pathlib import Path
import time
import re

def detect_language(text: str, default_voice: str):
    # 自动识别中英文
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
    return default_voice if has_chinese else "en-US-AriaNeural"

async def _tts_once(text: str, output: Path, voice: str, rate: str):
    if not text.strip(): return False
    final_voice = detect_language(text, voice)
    communicate = edge_tts.Communicate(text, final_voice, rate=rate)
    await communicate.save(str(output))
    return True

def text_to_mp3(text: str, output: Path, voice="zh-CN-YunxiNeural", rate="0%", max_retry=3):
    # 彻底过滤非法字符，防止微软接口因特殊符号报错导致合成中断
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    for attempt in range(1, max_retry + 1):
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            asyncio.run(_tts_once(text, output, voice, rate))
            # 物理限速，保护 IP
            time.sleep(0.8) 
            return True
        except Exception as e:
            print(f"⚠️ TTS 尝试 {attempt} 失败: {e}")
            time.sleep(attempt * 2)
    return False