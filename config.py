import sys

WHISPER_MODEL  = "base"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 5
SILENCE_THRESH = 0.01
LANGUAGE       = "ru"

# qwen2.5:3b — влезает в 6 ГБ VRAM, понимает русский, быстро отвечает
# если хочешь лучше качество и есть терпение — qwen2.5:7b (чуть медленнее)
LLM_MODEL    = "qwen2.5:3b"
VISION_MODEL = "llava:7b"

if sys.platform.startswith("win"):
    PLATFORM = "windows"
elif sys.platform.startswith("darwin"):
    PLATFORM = "mac"
else:
    PLATFORM = "linux"
