#!/usr/bin/env python

import argparse
import os
from mido import Message, MidiFile
import fluidsynth
import subprocess
from pydub import AudioSegment
from pedalboard import Reverb
import numpy as np


def modify_midi(midi_in: str, program_number = 0) -> str:
    """Change the instrument (program number) in a MIDI file."""
    mid = MidiFile(midi_in)
    for track in mid.tracks:

        for i, msg in enumerate(track):

            if msg.type == 'program_change':  
                # modify existing program
                msg.program = program_number
            elif msg.type == 'note_on' or msg.type == 'note_off':

                if i == 0 or (i > 0 and track[i-1].type != 'program_change'):
                    # insert a program change before the first note
                    track.insert(i, Message('program_change', program=program_number, channel=msg.channel, time=0))

    midi_out = f"{midi_in}.aux"
    mid.save(midi_out)
    return midi_out


def synthesis(midi_file: str, soundfont: str) -> AudioSegment:
    """ syntesize audio with midi input using system fluidsynt """
    wave = '/tmp/temp.wav'
    subprocess.run(["fluidsynth", "-ni", soundfont, midi_file, "-F", wave, "-r", "44100"], check = True)
    return AudioSegment.from_wav(wave)

    
def process_audio(audio: AudioSegment, volume: int, reverb: bool) -> AudioSegment:
    """ process audio """
    if reverb: return apply_reverb(audio) + volume
    return audio + volume


def export_mp3(audio: AudioSegment, mp3_file: str, title = "unknown", artist = "unknown", genre = 42):
    """ export mp3 audio file """
    audio.export(mp3_file, format = "mp3", tags = {"title": title, "artist": artist}) #, "genre": genre})


def apply_reverb(audio: AudioSegment) -> AudioSegment:
    """ high-quality reverb with pedalboard """
    samples = np.array(audio.get_array_of_samples(), dtype = np.float32)
    if audio.sample_width == 2: samples /= 32768.0 # 16-bit audio
    elif audio.sample_width == 3: samples /= 8388608.0 # 24-bit audio (rare)
    sr = audio.frame_rate    
    processed_samples = Reverb(room_size = 0.75, damping = 0.5, wet_level = 0.3).process(samples, sr)
    processed_samples = (processed_samples * 32768.0).astype(np.int16) # back to 16-bit
    return AudioSegment(processed_samples.tobytes(), frame_rate = sr, sample_width = 2, channels = audio.channels)


def get_instrument(synth: fluidsynth.Synth, font: str, bank: int, program: int) -> str:

    synth.program_select(0, font, bank, program)
    instrument = synth.channel_info(0)[3]
    return instrument


def dump_font(fs, sfid):

    for bank in range(1):

        for program in range(128):

            #fs.program_select(0, sfid, bank, program)
            #instrument = fs.channel_info(0)[3]
            instrument = get_instrument(fs, sfid, bank, program)
            if instrument != 'Gun Shot':

                print(bank, program, instrument, end = " ")
    print()


def main():

    default_font = os.getenv('FLUID_SF2', 0)
    if not default_font:

        print('cannot find sound font\ni am dead')
        return
    default_midi = 'last.mid'
    default_inst = 4
    default_volume = 16
    parser = argparse.ArgumentParser(description = "a command-line utility to convert midi to mp3 written in python")
    parser.add_argument('-m', '--midi',       type = str, default = default_midi,   help = f"midi input file (default is {default_midi}.mp3)")
    parser.add_argument('-o', '--output',     type = str, default = 0,              help = f"output mp3 file name (default is {default_midi})")
    parser.add_argument('-f', '--font',       type = str, default = default_font,   help = f"sound font pathname (default is {default_font})")
    parser.add_argument('-i', '--instrument', type = int, default = default_inst,   help = f"midi program number (default is {default_inst})")
    parser.add_argument('-v', '--volume',     type = int, default = default_volume, help = f"mp3 volume (default is {default_volume})")
    parser.add_argument('-r', '--reverb',                  action = "store_true",   help = "apply reverb")
    parser.add_argument('-p', '--programs',                action = "store_true",   help = "list midi programs")
    args = parser.parse_args()

    print(f"instrument: {args.instrument}, input: {args.midi}")

    fs = fluidsynth.Synth()
    # fs.start()
    sfid = fs.sfload(args.font)

    if args.programs:

        dump_font(fs, sfid)
        return
    if not os.path.exists(args.midi):

        print(f"{args.midi} not found\ni am dead")
    else:

        jack = os.path.splitext(args.midi)
        title = jack[0]
        mp3 = f"{args.midi}.mp3"
        if args.output: mp3 = args.output

        midi_aux = modify_midi(args.midi, args.instrument)
        au = synthesis(midi_aux, args.font)
        pau = process_audio(au, args.volume, args.reverb)
        export_mp3(pau, mp3, title  = title, artist = 'Kaloyan Krastev', genre = 420)
        subprocess.run(["rm", midi_aux])

        instrument = get_instrument(fs, sfid, 0, args.instrument)
        print("= " * 33)
        print(f"synthesized {mp3} from {args.midi} with {args.instrument} {instrument}")


if __name__ == "__main__":
    main()
