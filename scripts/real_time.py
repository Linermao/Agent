import pyaudio
import wave
import numpy as np
import time
from faster_whisper import WhisperModel
from scripts.config import load_config

configs = load_config()

FORMAT = pyaudio.paInt16
CHANNELS = configs["CHANNELS"]
RATE = configs["RATE"]
CHUNK = configs["CHUNK"]
RECORD_SECONDS = configs["RECORD_SECONDS"]  # record seconds
SILENCE_THRESHOLD = configs["SILENCE_THRESHOLD"]  # mute threshold
SILENCE_DURATION_TO_STOP = configs["SILENCE_DURATION_TO_STOP"]  # how long after the user stops talking to stop recording (seconds)
OUTPUT_PATH = configs["OUTPUT_PATH"] # if you need to save input audio, change this to your path
MODEL_SIZE = configs["MODEL_SIZE"] # choose from large-v2, medium, small (defualt), tiny
MODEL_PATH = configs["MODEL_PATH"] # your faster-whisper model loacl path

# run on GPU with FP16
# model = WhisperModel(MODEL_SIZE or MODELPATH, device="cuda", local_files_only=True)
# or run on GPU with INT8
# model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

# set pyaudio parameters

def record_audios():
    # initialize PyAudio
    audio = pyaudio.PyAudio()
    # open audio stream
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    print("Recording begins. Please speak...")
    frames = []
    silence_start = None
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        is_silence = np.mean(np.abs(audio_data)) < SILENCE_THRESHOLD

        if is_silence:
            if silence_start is None:
                silence_start = time.time()
            elif time.time() - silence_start > SILENCE_DURATION_TO_STOP:
                # print("Mute detected, stop recording...")
                break
        else:
            silence_start = None

    print("End of recording, transcribing...")

    # close audio stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    """
    # save input audio as wave file
    wf = wave.open(OUTPUT_PATH, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"the input audio has saved to {OUTPUT_PATH}")
    """
    return frames

def to_text(frames):
    # Convert captured data to numpy array
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).flatten().astype(np.float32)/32768.0 

    segments, info = model.transcribe(audio_data, beam_size=5, language="en", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=1000))

    # print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    text = []

    for segment in segments:
        # print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        # print(segment.text)
        text.append(segment.text)

    combined_text = ", ".join(text)

    return combined_text

if __name__ == "__main__":
    frames = record_audios()
    text = to_text(frames)
    print(text)