# ORCA

ORCA generates an equalizer that corrects a loudspeaker's in-room frequency response (FR) toward a specified target curve.

Most room correction algorithms create parametric filters to improve a loudspeaker's in-room FR.

ORCA creates a detailed GraphicEQ definition that can be imported into software equalizers such as Equalizer APO or Wavelet.

This is especially useful for applying room correction to a Bluetooth speaker through Wavelet.

You can customize the target curve and the generated equalizer.

## Usage

To use the algorithm, you need to export FR measurements as *.txt files from REW.
![Average fr of all measurements](https://user-images.githubusercontent.com/28658521/193836087-6095f64e-2b85-4b0f-8038-55ae23231b57.png)

Install the project locally:

        pip install -e .

If you want to use diagnostic plots, install the optional plotting dependency:

        pip install -e ".[plot]"

The simplest way is to either supply a list of paths to REW files or a directory with the files.

        from orca import get_graph_eq_str

        eq_str = get_graph_eq_str(file_paths=["path/to/file1", "path/to/file2", "path/to/file3"])
        # Or if all measurements are inside a directory:
        eq_str = get_graph_eq_str(measurements_dir="path/to/measurement/dir")

You can also run the command line entrypoint:

        orca-eq --measurements-dir "example measurements"

The equivalent Python module entrypoints are also available:

        python -m orca --measurements-dir "example measurements"
        python -m orca.cli --measurements-dir "example measurements"

For a band-limited measurement, choose the frequency range used for SPL normalization explicitly:

        from orca.EQConfig import EQConfig

        subwoofer_config = EQConfig.from_range(eq_from=20, eq_to=80, eq_res=32)
        eq_str = get_graph_eq_str(
            measurements_dir="path/to/subwoofer/measurements",
            eq_config=subwoofer_config,
            reference_range=(30, 80),
        )

        orca-eq --measurements-dir "path/to/subwoofer/measurements" --eq-from 20 --eq-to 80 --eq-res 32 --reference-from 30 --reference-to 80

From a checkout, you can also run `python main.py --measurements-dir "example measurements"`.

By default, the target curve is flat and the equalizer contains 128 logarithmically spaced points from 20 to 20000 Hz.

Measurements are level-normalized against the shared 100-10000 Hz range by default.
This range provides a useful SPL reference for full-range measurements without letting bass roll-off, room modes, or high-frequency directivity dominate the level estimate.
Use `reference_range` to select another range for band-limited measurements.
Every measurement must fully cover the selected range.
All positive frequencies from the REW export are preserved, including values below 20 Hz.
All supplied measurements must use the same logarithmic frequency grid.
ORCA evaluates the equalizer at every point of that native measurement grid while optimizing only the GraphicEQ control points that will be exported.

With `verbose=True` or the CLI's `--verbose` flag, ORCA reports the level-aligned mean absolute deviation from the target and its 95th percentile for the original and estimated equalized responses.
Diagnostics are written to standard error so standard output remains a valid GraphicEQ definition.
Level alignment excludes the overall playback-volume change introduced by anchoring the maximum EQ gain at 0 dB while retaining every frequency-dependent error.

More usage examples are available in `examples.py`.

ORCA adjusts the target curve to the measured bass response to avoid excessive boost, reduced overall volume, and distortion.
![Adjusted target curve](https://user-images.githubusercontent.com/28658521/193834396-a3b99590-4d1f-4b0b-bd5f-9eb6920f142c.png)

In the next step, an equalization curve is created to minimize the deviation from the target.

The EQ curve becomes smoother toward higher frequencies.
Custom weighting functions can change this behavior.

![Created eq](https://user-images.githubusercontent.com/28658521/193834404-aaa57282-302e-454b-a4cc-78070a3bf154.png)

You also get an estimation of the in-room FR after equalization.
![FR after eq estimation](https://user-images.githubusercontent.com/28658521/193834392-6f8e556e-2a90-462a-bfc5-82cb79dc3485.png)
## Customizing

Pass an `EQConfig` to `get_graph_eq_str` or `create_eq` to customize the generated EQ definition.

### EQConfig

        from orca.EQConfig import EQConfig

`EQConfig.from_range(eq_from=20, eq_to=20000, eq_res=128)` creates logarithmically spaced integer control points between the supplied frequency bounds.

- `eq_points` can be supplied instead of `eq_from`, `eq_to`, and `eq_res`.
  The points must be finite, positive, unique, and strictly increasing.
- `set_max_zero=True` anchors the maximum EQ gain at 0 dB.
  The complete curve is shifted while preserving the relative differences between EQ points.
- `max_boost=10` sets the maximum boost when `set_max_zero=False`.
  The value must have at most one decimal place to match the exported GraphicEQ gains.
- `weighting_fun` applies weighting based on the smoothing factor and frequency.

Wavelet's fixed GraphicEQ frequency layout lives in its own module:

        from orca import wavelet_config

        eq_config = wavelet_config()

`format_eq_str(eq_curve)` serializes the curve's existing control points and values without applying additional constraints.
Pass `format_eq_str(eq_curve, config=eq_config)` when the curve should be resampled to another configured point grid or have that config's output constraints applied.

## Development

Run the complete test suite from the repository root with:

        python -m unittest discover -v

Install the development dependencies and run the quality checks with:

        pip install -e ".[dev]"
        python -m ruff check .
        python -m ruff format --check .
        python -m mypy

## The Algorithm

To compute an equalizer, ORCA optimizes the configured GraphicEQ control-point gains directly.
The piecewise-linear curve produced by those points is evaluated at every frequency in the original measurement grid.
If that grid is too sparse to constrain every control-point gain, ORCA supplements it with the configured control frequencies.
This ensures that the optimization sees every degree of freedom in the same finite-resolution filter that will be exported.

For each of the frequencies, the process is as follows:

We take a strongly smoothed version of each measurement and compare the target level to the current SPL.
Smoothing widths are defined in octaves, so they do not change when the measurement grid has a different point density.

We look for a dB adjustment at every measured frequency to minimize the error between the target and equalized SPL.
A least-squares projection then finds the GraphicEQ point updates whose interpolated curve best realizes those adjustments over the complete measurement grid.

The boost is adjusted over multiple iterations with decreasingly smoothed measurements.

In each iteration, we take the difference between the adjusted current level and the target level.

This difference gets weighted and added to the current dB adjustment.

We repeat this process until reaching the raw, unsmoothed measurements.

Higher frequencies and later iterations reduce the amount by which the boost changes.

This creates an EQ that becomes smoother toward higher frequencies.
Pass a custom weighting function to `EQConfig` to change the weighting process.

## License

ORCA is available under the [MIT License](LICENSE).
