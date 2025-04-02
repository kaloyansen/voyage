#!/usr/bin/env python

import os
from mido import Message, MidiFile
import fluidsynth
import subprocess
from pydub import AudioSegment
import argparse


def modify_midi_instrument(midi_in, midi_out, program_number = 0):
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

    mid.save(midi_out)

def midi_to_mp3(midi_file, soundfont, mp3_file, title = "unknown", artist = "unknown", genre = "unknown"):
    """Convert MIDI to MP3 using FluidSynth and add metadata."""
    wav_file = "temp.wav"
    subprocess.run(["fluidsynth", "-ni", soundfont, midi_file, "-F", wav_file, "-r", "44100"], check = True)
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format = "mp3", tags = {"title": title, "artist": artist, "genre": genre})
    subprocess.run(["rm", wav_file])


def increase_volume(input_mp3, output_mp3, db_increase = 5):

    audio = AudioSegment.from_file(input_mp3, format = "mp3")
    louder_audio = audio + db_increase
    louder_audio.export(output_mp3, format = "mp3")


def get_instrument(synth, font, bank, program):

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
    default_volume = 10
    parser = argparse.ArgumentParser(description = "a command-line utility to convert midi to mp3 written in python")
    parser.add_argument('-m', '--midi',   type = str, default = default_midi,   help = f"midi input file (default is {default_midi})")
    parser.add_argument('-f', '--font',       type = str, default = default_font,   help = f"sound font pathname (default is {default_font})")
    parser.add_argument('-i', '--instrument', type = int, default = default_inst,   help = f"midi program number (default is {default_inst})")
    parser.add_argument('-v', '--volume',     type = int, default = default_volume, help = f"mp3 volume (default is {default_volume})")
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

        midi_aux = f"{title}.mid.aux"
        mp3_out = f"{title}.mp3"
        mp3_aux = f"{title}.mp3.aux"

        modify_midi_instrument(args.midi, midi_aux, args.instrument)
        midi_to_mp3(midi_aux,
                    args.font,
                    mp3_aux,
                    title  = title,
                    artist = 'Kaloyan Krastev',
                    genre = 'medievale')
        increase_volume(mp3_aux, mp3_out, args.volume)
        instrument = get_instrument(fs, sfid, 0, args.instrument)
        print("= " * 33)
        print(f"synthesized {mp3_out} from {args.midi} with {args.instrument} {instrument}")


if __name__ == "__main__":
    main()
