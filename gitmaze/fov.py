"""Field of View (FOV) calculation using symmetric shadowcasting."""
from typing import Set, Tuple, Callable


class FOV:
    """Computes field of view on a 2D grid."""

    # 8 octants: (xx, xy, yx, yy)
    MULT = (
        (1, 0, 0, -1),
        (0, 1, -1, 0),
        (0, -1, -1, 0),
        (-1, 0, 0, -1),
        (-1, 0, 0, 1),
        (0, -1, 1, 0),
        (0, 1, 1, 0),
        (1, 0, 0, 1),
    )

    @classmethod
    def compute(
        cls,
        start_x: int,
        start_y: int,
        radius: int,
        is_transparent: Callable[[int, int], bool],
    ) -> Set[Tuple[int, int]]:
        """Compute the set of visible coordinates (x, y) from (start_x, start_y)."""
        visible: Set[Tuple[int, int]] = {(start_x, start_y)}

        for octant in range(8):
            cls._cast_light(
                start_x,
                start_y,
                1,
                1.0,
                0.0,
                radius,
                cls.MULT[octant],
                is_transparent,
                visible,
            )

        return visible

    @classmethod
    def _cast_light(
        cls,
        cx: int,
        cy: int,
        row: int,
        start_slope: float,
        end_slope: float,
        radius: int,
        mult: Tuple[int, int, int, int],
        is_transparent: Callable[[int, int], bool],
        visible: Set[Tuple[int, int]],
    ):
        if start_slope < end_slope:
            return

        radius_sq = radius * radius
        xx, xy, yx, yy = mult

        for distance in range(row, radius + 1):
            dx = -distance - 1
            dy = -distance
            blocked = False
            new_start = start_slope

            while dx <= 0:
                dx += 1
                # Translate relative coordinates to map coordinates
                mx = cx + dx * xx + dy * xy
                my = cy + dx * yx + dy * yy

                # Calculate left and right slope of current cell
                l_slope = (dx - 0.5) / (dy + 0.5)
                r_slope = (dx + 0.5) / (dy - 0.5)

                if start_slope < r_slope:
                    continue
                elif end_slope > l_slope:
                    break

                # Check if cell is within radius circle
                if (dx * dx + dy * dy) <= radius_sq:
                    visible.add((mx, my))

                if blocked:
                    if not is_transparent(mx, my):
                        new_start = r_slope
                        continue
                    else:
                        blocked = False
                        start_slope = new_start
                else:
                    if not is_transparent(mx, my) and distance < radius:
                        blocked = True
                        cls._cast_light(
                            cx,
                            cy,
                            distance + 1,
                            start_slope,
                            l_slope,
                            radius,
                            mult,
                            is_transparent,
                            visible,
                        )
                        new_start = r_slope

            if blocked:
                break
