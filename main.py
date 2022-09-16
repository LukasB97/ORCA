import EQConfig
import TargetCurves
from RewToGraphEq import create_eq

TargetCurves.downwards_slope(factor=0.6).draw()

eq = create_eq(
    target_curve=TargetCurves.linear(),
    measurements_dir="../example measurements",
    # file_paths=["C:\\Users\Lukas\\Documents\\Measurements\\Export\\BPHS\\1.txt"],
    eq_config=EQConfig.EQConfig(
        room_correction_config=EQConfig.RoomCorrectionConfig(std_influence=9)
    ))

eq.draw()
