# it2p8.py
This is a simple Python script to generate Pico-8 music files from `.it` files. The objective in doing this is to make it easier to compose for Pico-8 by freeing composers from the constrained Pico-8 music editor while still obeying the sound engine limitations. [Here's an example of it in action](https://twitter.com/maplesbian/status/1148878267316932608)

### Disclaimer

This tool was developed lazily for my own personal usage. I have not made efforts in making it particularly user-friendly or even crash-proof. You are welcome to improve on it for yourself or submit issues with suggestions and requests, but as it stands, it's a tool aimed at myself alone, and the code is very jank in places. Nevertheless, I wanted to share it with others since I believe in always sharing my processes and methods.

## Usage

The converter is called by:

```python3 it2p8.py input.it [output.p8]```

where `input.it` is a specifically-designed ImpulseTracker module. I recommend OpenMPT, but any other ImpulseTracker editor should work fine.

### How the `.it` file must be structured

The converter looks at the orderlist and pattern data alone. Right now, everything else is ignored. Your file must have 4 channels and your patterns must be all 32 rows in length.

The included `test.it` file in this repository contains samples of the standard instruments 0-7, plus some custom SFX instruments. In order to use other SFX instruments 8-F, you must sample them yourself and include them in order after the standard instruments. The converter looks at what instrument number is being used in order to determine the Pico-8 instrument, so they must be in the same order. You must also include the SFX strings of your custom instruments in the song message in order for them to be included back in the output pico-8 cartridge. The root note used is C-5 in IT, matching to C-2 in Pico-8.

The volume column is parsed and remapped from a range of 0-64 to 0-7 to fit the pico-8 volume. This gives you less direct control over the final output, for the sake of more accurate playback when hearing your song as the original `.it` file.

The effects column is mapped in a similar way in order to match the sound between playbacks, however with obvious limitations. Effect command values are ignored, since they aren't present in pico-8. The mapping is as follows:

| IT effect | Pico-8 effect       |
| --------- | -------------       |
| `Dx0`     | Effect 4 - Fade In  |
| `D0x`     | Effect 5 - Fade Out |
| `Gxx`     | Effect 1 - Slide    |
| `Hxx`     | Effect 2 - Vibrato  |
| `Exx`     | Effect 3 - Drop     |

## FAQ

1. Why didn't you program in the arpeggio effects 6 and 7?

Personally, I don't like those effects since I have never been able to get a good effect out of them, and thus prefer using SFX instruments for arp macros. Additionally, the way the `Jxy` command works for arpeggio in the ImpulseTracker format can't be easily translated over to the Pico-8 arp commands, which use 4 notes.

## TODO: Improvements I want to make some day

1. A second script which generates an `.it` samplepack based on a Pico-8 cartridge with the custom SFX instruments so you don't have to build one by hand.

## License

I am releasing this code under the Mozilla license since I want others to be able to build upon this if they want to compose for Pico-8 games more easily. If you do use this in your project (either as a tool or bundling it in somewhere else) please credit me somewhere, and please let me know! I'd love to hear from others using what I've made.
