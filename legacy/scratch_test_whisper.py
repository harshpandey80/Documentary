import time
import os
from pathlib import Path
import psutil
from faster_whisper import WhisperModel

video = Path('workspace/runs/history_of_england_v3/10_england_v3_subtitled.mp4')
audio_wav = Path('workspace/runs/history_of_england_v3/extracted_audio.wav')
os.system(f'ffmpeg -y -nostats -loglevel error -i "{video}" -ar 16000 -ac 1 "{audio_wav}"')

t0 = time.time()
mem0 = psutil.Process().memory_info().rss / 1024 / 1024
print("Loading faster-whisper base int8 on CPU...")
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(str(audio_wav), word_timestamps=True)
words = []
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    if segment.words:
        for word in segment.words:
            words.append((round(word.start, 2), round(word.end, 2), word.word.strip()))

mem1 = psutil.Process().memory_info().rss / 1024 / 1024
print(f"Transcription complete in {time.time()-t0:.2f}s, Peak RAM: {mem1:.1f} MB (delta {mem1-mem0:.1f} MB)")
print(f"Total words: {len(words)}")
if words:
    print(f"First word: {words[0]}")
    print(f"Last word: {words[-1]}")
