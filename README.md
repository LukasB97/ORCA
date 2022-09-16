
ORCA is an algorithm developed for generating an equalizer to
correct the in-room frequency response of a loudspeaker to a specific target.

Most room correction algorithms create parametric filters
to improve the in-room response of a loudspeaker.

This algorithm creates a config for a detailed graphical equalizer that can be
imported into software equalizers like EQApo or Wavelet.

This is especially useful when you want to do room correction for a bluetooth speaker
(Wavelet)

After specifying a target curve,
the algorithm works by evaluating boost levels for specific hz values.

The Hz values, eq-resolution etc. can be changed in a config.

Usage

In order to use the algorithm, you need exported frequency response measurements from rew.
The function create_eq is the entry point for this.

The simplest way is to either, supply a list of paths to req files or a directory with the files.

create_eq(file_paths=["measurement1.txt", "measurement2.txt","measurement3.txt"])
or
create_eq(measurements_dir="path/to/measurements")

In this case, the target curve is linear and the equalizer is created with 128 log-spaced points
in the 20-20000 Hz range.

Customizing

It is possible to customize the room-correction process, as well as the properties of
the created eq file.

room-correction process
weighting_fun: Callable[[int, float], float] = WeightingFuns.default
max_boost: the maximum db boost that will be applied.
on_target_freq: The frequency at which the algorithm tries to match the specified target curve. 
For frequencies below on_target_freq, the target curve will be adjusted, based on the frequency
response of the loudspeaker, to create a smooth bass-response
std_influence ([0, ..., 9]): The amount, to which the standard deviation of the different 
measurements at a given frequency impacts the strength of the boost level.
For a frequency with high standard deviation between the measurements,
a low std_influence will 
A high value will lead to a low adjustment boost adjustment at a given frequency,
if the standard deviation at this frequency is high.


EQ-Config
eq_from: Lowest frequency to generate eq for
eq_to: Highest frequency to generate eq for
eq_res: The number of eq points. If supplied, eq_res log-spaced points will be computed
between eq_from and eq_to.
eq_points: Can be supplied instead of eq_from, eq_to and eq_res. In this case,
the eq points are supplied instead  not computed and
set_max_zero=True: Determines, if the max boost value of the created eq
get anchored at 0 db, in order not to introduce distortion
formatter
                 room_correction_config: RoomCorrectionConfig = RoomCorrectionConfig()


This can be customized by supplying a custom target curve and/or an eq config.


The algorithm:

The boost is computed, by looking at the target level and
spls of the measurements.

In multiple iterations, the boost gets recalculated
based on smoothed versions of the measurements. 
The impact of a smoothed measurement depends on the Hz value.
The higher the Hz value, the higher the impact of strongly smoothed curves.

The specific weighting of .. can be changed by supplying a custom weighting function.

It is possible to extend the weighting,
by also using the standard deviation to influence the strength of the boost level






evaluating the difference between the current spl
and the target level. 
