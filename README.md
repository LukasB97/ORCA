# ORCA
is an algorithm developed for generating an equalizer to
correct the in-room frequency response of a loudspeaker to a specific target curve.

Most room correction algorithms create parametric filters
to improve the in-room response of a loudspeaker.

This algorithm creates a config for a detailed graphical equalizer that can be
imported into software equalizers like EQApo or Wavelet.

This is especially useful when you want to do room correction for a bluetooth speaker
(Wavelet)

You can customize the target curve and certain parameters of equalizer you want to create.

## Usage

To use the algorithm, you need to export frequency response measurements as *.txt files from REW.
The function create_eq is the entry point for this.

The simplest way is to either supply a list of paths to req files or a directory with the files.

        eq_str = get_graph_eq_str(file_paths=["path/to/file1", "path/to/file2", "path/to/file3"])
        # Or if all measurements are inside a directory:
        eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir")

In this case, the target curve is linear, and the equalizer is created with 128 log-spaced points
in the 20-20000 Hz range.

## Customizing

It is possible to customize the properties of the created eq definition.
Just pass your own EQConfig to get_graph_eq_str or create_eq


EQ-Config

        eq_from=20: Lower bound for eq frequencies
        eq_to=20000: Upper bound for eq frequencies
        eq_res=128: The number of eq points.
        If supplied, eq_res log-spaced points will be computed between eq_from and eq_to.
        
        eq_points: Can be supplied instead of eq_from, eq_to and eq_res. In this case,
        the eq points are supplied instead of being computed
        set_max_zero=True: Determines, if the max boost value of the created eq
        get anchored at 0 db, in order not to introduce distortion
        max_boost=10: the maximum db boost that will be applied.
        weighting_fun: function that applies weighting based on smooting factor and frequency


## The Algorithm

To compute an equalizer, 512 boost levels for log spaced frequencies are evaluated.

For each of the frequencies, the process is as follows:

We take a strongly smoothed version of all the measurements,
and compare the level of our target curve to the current spl.

We look for a dB adjustment at this frequency to minimize the error between target-spl and equalized-spl.


In multiple iterations, the boost gets adjusted, by
repeating the above process with decreasingly smoothed measurements.

In each iteration, we take the difference, between the current level + dB adjustment
and the target level.

This difference gets weighted and added to the current dB adjustment.

We repeat this process until we used the raw (no smoothing) measurements.

Higher frequencies and number of the current iteration decrease the factor
to which the boost gets changed.

This way, we create an eq that gets more smooth, the higher the frequency gets.
The weighting process can be changed by supplying a custom weighting function
to the constructor of the EQConfig.


