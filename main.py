import EQConfig
import TargetCurves
from RewToGraphEq import create_eq


eq = create_eq(
    target_curve=TargetCurves.linear(),
    measurements_dir="./example measurements/lz",
    # file_paths=["C:\\Users\Lukas\\Documents\\Measurements\\Export\\BPHS\\1.txt"],
    eq_config=EQConfig.EQConfig()
)

#eq.draw()
