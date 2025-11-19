import json
import os
from pydub import AudioSegment

class AudioMixer:
    def __init__(self, output_dir: str = "story_output"):
        self.output_dir = output_dir

    def load_timeline(self, json_filename: str):
        path = os.path.join(self.output_dir, json_filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find timeline file: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def mix(self, timeline_json: str, output_filename: str = "final_story_mixed.wav"):
        print(f"\n[Mixer] Loading timeline: {timeline_json}...")
        data = self.load_timeline(timeline_json)
        
        # 1. Load Narration
        narration_file = os.path.join(self.output_dir, data['narration_file'])
        print(f"[Mixer] Loading base track: {data['narration_file']}")
        final_audio = AudioSegment.from_file(narration_file)
        
        # 2. Overlay SFX
        cues = data.get('cues', [])
        print(f"[Mixer] Found {len(cues)} sound effects to mix.")
        
        for cue in cues:
            sfx_file = os.path.join(self.output_dir, cue['file'])
            if not os.path.exists(sfx_file):
                print(f"  Warning: File missing {sfx_file}, skipping.")
                continue
                
           
            sound = AudioSegment.from_file(sfx_file)
            if cue.get('volume_db', 0) != 0:
                sound = sound + cue['volume_db']
                
            # Calculate position in milliseconds
            position_ms = int(cue['time_sec'] * 1000)
            
            print(f"  -> Mixing '{cue['description']}' at {cue['time_sec']}s")
            
            # Overlay 
            if position_ms < len(final_audio):
                final_audio = final_audio.overlay(sound, position=position_ms)
            else:
                # Extend audio if sound starts after narration ends
                silence_gap = position_ms - len(final_audio)
                if silence_gap > 0:
                    final_audio = final_audio + AudioSegment.silent(duration=silence_gap)
                final_audio = final_audio + sound

        # 3. Export
        output_path = os.path.join(self.output_dir, output_filename)
        final_audio.export(output_path, format="wav")
        print("\n" + "="*60)
        print(f"MIXING COMPLETE. Saved to: {output_path}")
        print("="*60)

if __name__ == "__main__":
    
    mixer = AudioMixer(output_dir="story_output")
    
    mixer.mix("timeline_for_mixer.json", "final_story_mixed.wav")