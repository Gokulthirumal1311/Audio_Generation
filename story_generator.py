import requests
import re
import os
import base64
from typing import List, Dict, Tuple
from pydub import AudioSegment
import time
import json
import io
from dotenv import load_dotenv


load_dotenv()


# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
ELEVENLABS_SOUND_URL = "https://api.elevenlabs.io/v1/sound-generation"
GEMINI_VOICE = "Aoede"

def generate_narration_gemini(text: str, output_file: str, voice_name: str = GEMINI_VOICE):
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    styled_text = f"Say naturally and expressively: {text}"
    data = {
        "contents": [{"parts": [{"text": styled_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}
            }
        }
    }
    print(f"Generating narration with Gemini (Voice: {voice_name})...")
    try:
        response = requests.post(GEMINI_TTS_URL, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            audio_data = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            audio_bytes = base64.b64decode(audio_data)
            wav_file = output_file.replace(".mp3", ".wav")
            audio_io = io.BytesIO(audio_bytes)
            audio = AudioSegment.from_raw(audio_io, sample_width=2, frame_rate=24000, channels=1)
            audio.export(wav_file, format="wav")
            print(f"Saved: {wav_file}")
            return wav_file
        else:
            print(f"Gemini Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Error generating narration: {str(e)}")
        return None

def generate_sound_effect(text_prompt: str, output_file: str, duration_seconds: int = 3):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text_prompt,
        "duration_seconds": duration_seconds,
        "prompt_influence": 0.3
    }
    print(f"Generating SFX: {text_prompt}")
    response = requests.post(ELEVENLABS_SOUND_URL, headers=headers, json=data)
    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Saved: {output_file}")
        return output_file
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

class StoryGenerator:
    def __init__(self, output_dir: str = "story_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        print(f"Generator initialized. Output folder: {output_dir}")

    def parse_story(self, story_text: str) -> Tuple[str, List[Dict]]:
        print("\n[1] Parsing story...")
        pattern = r'\[([^\]]+)\]'
        sound_cues = []
        for match in re.finditer(pattern, story_text):
            sound_description = match.group(1)
            position = match.start()
            text_before = story_text[:position]
            clean_before = re.sub(pattern, '', text_before)
            sound_cues.append({
                'description': sound_description,
                'position': len(clean_before),
            })
        clean_text = re.sub(pattern, '', story_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text, sound_cues

    def estimate_timing(self, clean_text: str, sound_cues: List[Dict]) -> List[Dict]:
        print("\n[2] Calculating timestamps...")
        words_per_minute = 122 
        for cue in sound_cues:
            text_before = clean_text[:cue['position']]
            words_before = len(text_before.split())
            time_seconds = (words_before / words_per_minute) * 60
            cue['time_sec'] = round(time_seconds, 2)
        return sound_cues

    def process(self, story_text: str, sfx_volume_db: float = 5.0):
        clean_text, sound_cues = self.parse_story(story_text)
        sound_cues = self.estimate_timing(clean_text, sound_cues)

        # 1. Generate Narration
        print("\n[3] Generating Narration...")
        narration_filename = "narration.wav"
        narration_path = os.path.join(self.output_dir, narration_filename)
        generate_narration_gemini(clean_text, narration_path)

        # 2. Generate SFX
        print("\n[4] Generating SFX...")
        mixer_cues = []
        for i, cue in enumerate(sound_cues):
            safe_desc = cue['description'][:20].replace(' ', '_')
            filename = f"sfx_{i+1}_{safe_desc}.mp3"
            filepath = os.path.join(self.output_dir, filename)
            
            generated_path = generate_sound_effect(cue['description'], filepath)
            
            if generated_path:
                # Data needed for the mixer
                mixer_cues.append({
                    "description": cue['description'],
                    "file": filename,
                    "time_sec": cue['time_sec'],
                    "volume_db": sfx_volume_db
                })
            time.sleep(1)

        # 3. Save Timeline JSON
        timeline_data = {
            "narration_file": narration_filename,
            "cues": mixer_cues
        }
        
        json_path = os.path.join(self.output_dir, "timeline_for_mixer.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(timeline_data, f, indent=2)
        
        print("\n" + "="*60)
        print("GENERATION COMPLETE")
        print(f"timeline saved to: {json_path}")
        print("Run 'audio_mixer.py' next!")
        print("="*60)

# --- MAIN ---
STORY_30SEC = """
Sarah approached the old mansion. [thunder rumbling]
The storm was getting worse. She reached for the rusty handle and
[door creaking open slowly] pushed the door open. Inside, everything
was dark and silent. [footsteps on wooden floor] Her footsteps echoed
through the empty halls. Suddenly, [glass shattering] a window broke
upstairs. [wind howling] The wind howled through the broken glass.
She wasn't alone. [door slamming shut] The door behind her slammed shut.
"""

if __name__ == "__main__":
    gen = StoryGenerator()
    gen.process(STORY_30SEC, sfx_volume_db=5.0)