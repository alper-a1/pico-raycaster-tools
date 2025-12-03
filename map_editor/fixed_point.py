import math

class ConversionHelpers:
    """
    Helper methods for fixed-point conversions and vector normalization.
    Kept in-file as its only needed by MapCanvasWidget.
    Required for player start position/angle conversions.
    """
    FIXED15_16_ONE = 1 << 16  # 65536
    
    @staticmethod
    def fixedpoint_to_float(fp: int) -> float:
        return fp / ConversionHelpers.FIXED15_16_ONE
    
    @staticmethod
    def fixedpoint_to_int(fp: int) -> int:
        return fp >> 16  # integer part only

    @staticmethod
    def float_to_fixedpoint(value: float) -> int:
        # 0.5 rounding factor for positive numbers
        # there should never be a negative value here
        return int(value * ConversionHelpers.FIXED15_16_ONE + 0.5) 
    
    @staticmethod
    def vector_to_fixed_unit(dx: float, dy: float) -> tuple[int, int]:
        mag = math.hypot(dx, dy)
        if mag == 0:
            return (ConversionHelpers.FIXED15_16_ONE, 0)
        ux = dx / mag
        uy = dy / mag
        return (int(round(ux * (ConversionHelpers.FIXED15_16_ONE))), int(round(uy * (ConversionHelpers.FIXED15_16_ONE))))
    
    