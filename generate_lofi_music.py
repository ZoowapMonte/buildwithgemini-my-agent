import math
import struct
import wave

def generate_lofi_track(filename="lofi_background_music.wav", duration_sec=15, sample_rate=44100):
    bpm = 85
    seconds_per_beat = 60.0 / bpm
    total_samples = int(duration_sec * sample_rate)
    
    # Frequencies for lo-fi chord progression (Cmaj7 -> Am7 -> Dm7 -> G7)
    chords = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7 (C4, E4, G4, B4)
        [220.00, 261.63, 329.63, 392.00],  # Am7 (A3, C4, E4, G4)
        [146.83, 174.61, 220.00, 261.63],  # Dm7 (D3, F3, A3, C4)
        [196.00, 246.94, 293.66, 349.23],  # G7 (G3, B3, D4, F4)
    ]
    
    chord_duration_beats = 4
    chord_duration_samples = int(chord_duration_beats * seconds_per_beat * sample_rate)
    
    samples = []
    
    for i in range(total_samples):
        t = i / sample_rate
        chord_idx = (i // chord_duration_samples) % len(chords)
        current_chord = chords[chord_idx]
        
        # Position within beat for drum click
        beat_pos = (t % seconds_per_beat) / seconds_per_beat
        
        # Base synth sound (soft Rhodes sine blend)
        synth_val = 0.0
        for freq in current_chord:
            # Main tone + warm octave sub
            tone = math.sin(2 * math.pi * freq * t) * 0.5
            warmth = math.sin(2 * math.pi * (freq * 0.5) * t) * 0.25
            synth_val += (tone + warmth)
            
        synth_val /= len(current_chord)
        
        # Rhythmic lo-fi beat (soft kick on beat 1 & 3, soft rim/snare on beat 2 & 4)
        current_beat = int(t / seconds_per_beat) % 4
        beat_decay = math.exp(-beat_pos * 8)
        
        drum_val = 0.0
        if current_beat in [0, 2] and beat_pos < 0.2:
            # Soft kick
            drum_val += math.sin(2 * math.pi * 60 * math.exp(-beat_pos * 15) * t) * 0.4 * beat_decay
        elif current_beat in [1, 3] and beat_pos < 0.15:
            # Soft rimshot noise/click
            noise = (math.sin(t * 12345.67) * 0.5)
            drum_val += noise * 0.2 * beat_decay
            
        # Subtle lo-fi vinyl crackle/warmth
        vinyl_crackle = math.sin(t * 8888.8) * 0.015
        
        mixed = (synth_val * 0.5) + drum_val + vinyl_crackle
        # Master volume clamp
        mixed = max(-0.95, min(0.95, mixed))
        
        # Convert to 16-bit PCM integer
        pcm_val = int(mixed * 32767)
        samples.append(pcm_val)
        
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        packed_data = struct.pack(f'<{len(samples)}h', *samples)
        wav_file.writeframes(packed_data)
        
    print(f"🎵 Generated upbeat lo-fi track: {filename} ({duration_sec}s)")

if __name__ == "__main__":
    generate_lofi_track()
