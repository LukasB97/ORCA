# ORCA
is an algorithm developed for generating an equalizer to
correct the in-room frequency response (FR) of a loudspeaker to a specified target curve.

Most room correction algorithms create parametric filters
to improve the in-room FR of a loudspeaker.

This algorithm creates a config for a detailed graphical equalizer that can be
imported into software equalizers like EQApo or Wavelet.

This is especially useful when you want to do room correction for a Bluetooth speaker
(Wavelet)

You can customize the target curve and certain parameters of equalizer you want to create.

## Usage

To use the algorithm, you need to export FR measurements as *.txt files from REW.
![Average fr of all measurements](https://user-images.githubusercontent.com/28658521/193836087-6095f64e-2b85-4b0f-8038-55ae23231b57.png)

Install the project locally:

        pip install -e .

If you want to use diagnostic plots, install the optional plotting dependency:

        pip install -e ".[plot]"

The simplest way is to either supply a list of paths to REW files or a directory with the files.

        from orca.RewToGraphEq import get_graph_eq_str

        eq_str = get_graph_eq_str(file_paths=["path/to/file1", "path/to/file2", "path/to/file3"])
        # Or if all measurements are inside a directory:
        eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir")

You can also run the command line entrypoint:

        orca-eq --measurements-dir "example measurements"

Running `python main.py --measurements-dir "example measurements"` still works from a checkout.

In this case, the target curve is linear, and the equalizer is created with 128 log-spaced points
in the 20-20000 Hz range.

Measurements are level-normalized against the shared 100-10000 Hz range by default. This avoids
letting bass roll-off, room modes, or high-frequency directivity dominate the level reference.
All supplied measurements must use the same logarithmic frequency grid. ORCA evaluates the
equalizer at every point of that native measurement grid while optimizing only the GraphicEQ
control points that will actually be exported.

With `verbose=True` (or the CLI's `--verbose` flag), ORCA reports the level-aligned mean absolute
deviation from the target and its 95th percentile for both the original and estimated equalized
response. Level alignment excludes the overall playback-volume change introduced by anchoring the
maximum EQ gain at 0 dB while retaining every frequency-dependent error.

More examples on the usage, are in the examples.py

The algorithm adjusts the target curve regarding the bass response of the measurements,
in order not to apply too much boost, as this leads to a lower overall volume and introduces distortion.
![Adjusted target curve](https://user-images.githubusercontent.com/28658521/193834396-a3b99590-4d1f-4b0b-bd5f-9eb6920f142c.png)

In the next step, an equalization curve is created to minimize the deviation from the target.

The smoothness of the eq-curve is increasing from low to high frequencies.
Different weighting functions can be used, to change the smoothing behaviour,
more on that later.

![Created eq](https://user-images.githubusercontent.com/28658521/193834404-aaa57282-302e-454b-a4cc-78070a3bf154.png)

You also get an estimation of the in-room FR after equalization.
![FR after eq estimation](https://user-images.githubusercontent.com/28658521/193834392-6f8e556e-2a90-462a-bfc5-82cb79dc3485.png)
## Customizing

It is possible to customize the properties of the created eq definition.
Just pass your own EQConfig to get_graph_eq_str or create_eq


EQ-Config

        eq_from=20: Lower bound for eq frequencies
        eq_to=20000: Upper bound for eq frequencies
        eq_res=128: The number of eq points.
        If supplied, eq_res log-spaced points will be computed between eq_from and eq_to.
        
        eq_points: Can be supplied instead of eq_from, eq_to and eq_res. They must be
        finite, positive, unique, and strictly increasing.
        set_max_zero=True: Determines, if the max boost value of the created eq
        gets anchored at 0 dB, in order not to introduce distortion. The complete
        curve is shifted, so the relative differences between EQ points are preserved.
        max_boost=10: the maximum dB boost that will be applied when set_max_zero=False.
        weighting_fun: function that applies weighting based on smoothing factor and frequency

## Development

Run the complete test suite from the repository root with:

        python -m unittest discover -v


## The Algorithm

To compute an equalizer, ORCA optimizes the configured GraphicEQ control-point gains directly.
The piecewise-linear curve produced by those points is evaluated at every frequency in the
original measurement grid. If that grid is too sparse to constrain every control-point gain,
ORCA supplements it with the configured control frequencies. This ensures that the optimization
sees every degree of freedom in the same finite-resolution filter that will later be exported. If
a direct API caller supplies a grid outside the normal 100-10000 Hz reference band, ORCA uses the
complete available grid for level alignment.

For each of the frequencies, the process is as follows:

We take a strongly smoothed version of each measurement. Smoothing widths are defined in
octaves, so they do not change when the measurement grid has a different point density,
and compare the level of our target curve to the current spl.

We look for a dB adjustment at every measured frequency to minimize the error between target SPL
and equalized SPL. A least-squares projection then finds the GraphicEQ point updates whose
interpolated curve best realizes those adjustments over the complete measurement grid.


In multiple iterations, the boost gets adjusted, by
repeating the above process with decreasingly smoothed measurements.

In each iteration, we take the difference between the current level + dB adjustment
and the target level.

This difference gets weighted and added to the current dB adjustment.

We repeat this process until we used the raw (no smoothing) measurements.

Higher frequencies and number of the current iteration decrease the factor
to which the boost gets changed.

This way, we create an eq that gets more smooth, the higher the frequency gets.
The weighting process can be changed by supplying a custom weighting function
to the constructor of the EQConfig.


