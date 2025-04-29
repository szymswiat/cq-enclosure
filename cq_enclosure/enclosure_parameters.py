from enum import Enum
from pydantic import BaseModel
import math


class NutPrintingWA(Enum):
    CUT_RECT_SPACES = 0
    ADD_CEILING = 1


class ScrewLocation(Enum):
    INSIDE_BOX = 0
    OUTSIDE_BOX = 1


class ScrewType(Enum):
    WOOD_SCREW = 0
    WITH_SQUARE_NUT = 1


class EnclosureParameters(BaseModel):
    # enclosure dimensions
    box_inner_width: float  # X
    box_inner_length: float  # Y
    box_inner_height: float  # Z

    # include screw cylinder dimensions in box_inner parameters when using ScrewLocation.INSIDE_BOX
    actual_inner_width: bool = True
    actual_inner_length: bool = True

    # splits into two solids: box and lid
    cut_top: float = 5.0

    # screw params, use actual dimensions
    screw_hole_diameter: float = 3.0 + 0.3
    screw_head_diameter: float = 6.0
    screw_total_length: float = 16.0
    # select screw placement
    screw_location: ScrewLocation = ScrewLocation.OUTSIDE_BOX
    screw_type: ScrewType = ScrewType.WOOD_SCREW
    # add additional screws in the middle of a wall
    corner_screws: bool = True
    middle_length_screws: bool = False
    middle_width_screws: bool = False

    # square nut parameters
    # use actual dimensions, spacing is added later
    square_nut_width: float = 5.5
    square_nut_height: float = 1.8
    nut_wa_type: NutPrintingWA = NutPrintingWA.ADD_CEILING

    # gasket parameters
    gasket_height: float = 1.6
    gasket_width: float = 1.2
    gasket_spacing: float = 0.15
    gasket_compression: float = 0.2

    # mount holders
    mount_holders: bool = True
    mount_holder_length: float = 15.0
    mount_holders_screw_hole_diameter: float = 5.0
    mount_holders_head_screw_diameter: float = 9.0
    mount_holders_fillet: bool = True

    # used for square nut printing trick
    layer_height: float = 0.28

    fillet_bottom: bool = True
    fillet_top: bool = True

    def initialize(self):
        self.square_nut_width += 0.4
        self.square_nut_height += 0.4
        self.screw_head_diameter += 0.5
        self.screw_total_length += 1

        if self.screw_location == ScrewLocation.INSIDE_BOX:
            if (
                self.corner_screws or self.middle_length_screws
            ) and self.actual_inner_width:
                self.box_inner_width = self.box_inner_width + 2 * (
                    2 * self.screw_cylinder_radius - self.wall_thickness
                )
            if (
                self.corner_screws or self.middle_width_screws
            ) and self.actual_inner_length:
                self.box_inner_length = self.box_inner_length + 2 * (
                    2 * self.screw_cylinder_radius - self.wall_thickness
                )

        if (
            self.mount_holders
            and self.middle_width_screws
            and self.screw_location == ScrewLocation.OUTSIDE_BOX
        ):
            self.mount_holder_length = max(
                self.mount_holder_length, math.ceil(self.screw_cylinder_radius * 4)
            )

    def validate(self):
        screw_options = (
            self.corner_screws,
            self.middle_length_screws,
            self.middle_width_screws,
        )
        if sum(screw_options) == 0:
            raise ValueError("Cannot generate enclosure without screws.")

        if self.screw_hole_diameter < 2.0 or self.screw_hole_diameter > 6.0:
            raise ValueError("Screw hole diameter must be between 2.0 and 6.0.")

        if self.box_inner_width > self.box_inner_length:
            raise ValueError("Inner width must be smaller or equal to inner length.")

        if (
            self.mount_holders
            and self.middle_width_screws
            and self.screw_location == ScrewLocation.OUTSIDE_BOX
        ):
            if self.mount_holder_length < self.screw_cylinder_radius * 4:
                raise ValueError(
                    f"mount_holder_length has to be at least {self.screw_cylinder_radius * 4} "
                    "for current parameters if additional_y_screws is True."
                )

        if (
            self.screw_location == ScrewLocation.OUTSIDE_BOX
            and self.box_inner_width < 31.0
            and self.mount_holders
            and self.corner_screws
        ):
            raise ValueError(
                "box_outer_width must be at least 31.0 if mount_holders "
                "are enabled and screws are outside the box."
            )

    # enclosure wall thickness
    @property
    def wall_thickness(self) -> float:
        return 3.0

    @property
    def bottom_and_lid_thickness(self) -> float:
        return 2.0

    @property
    def screw_cylinder_fillet(self) -> float:
        return 2.0 + 1e-3

    @property
    def inner_fillet(self) -> float:
        return 2.0 + 2 * 1e-3

    @property
    def bottom_lid_fillet(self) -> float:
        return 1.0

    @property
    def outer_vertical_edges_fillet(self) -> float:
        return 2.0 + 1e-3

    @property
    def gasket_fillet(self) -> float:
        return 2.0 + 4 * 1e-3

    @property
    def screw_cylinder_radius(self) -> float:
        base_radius = max(self.screw_hole_diameter, 3.0)
        if self.screw_type == ScrewType.WITH_SQUARE_NUT:
            nut_radius = (self.square_nut_width * math.sqrt(2)) / 2
            base_radius = max(nut_radius, base_radius)
        return base_radius + 1.6

    @property
    def square_nut_depth_placement(self) -> float:
        return self.screw_total_length - 4.0

    @property
    def lid_screw_hole_diameter(self) -> float:
        return self.screw_hole_diameter + 1.0

    @property
    def box_screw_hole_radius(self) -> float:
        return self.screw_hole_diameter / 2

    @property
    def box_outer_width(self) -> float:
        return self.box_inner_width + 2 * self.wall_thickness

    @property
    def box_outer_length(self) -> float:
        return self.box_inner_length + 2 * self.wall_thickness

    @property
    def box_outer_height(self) -> float:
        return self.box_inner_height + 2 * self.bottom_and_lid_thickness

    @property
    def gasket_in_slot_distance(self) -> float:
        return self.gasket_spacing * 2

    @property
    def gasket_slot_outer_width(self) -> float:
        return (
            self.box_outer_width
            - self.wall_thickness
            + self.gasket_width
            + self.gasket_in_slot_distance
        )

    @property
    def gasket_slot_outer_length(self) -> float:
        return (
            self.box_outer_length
            - self.wall_thickness
            + self.gasket_width
            + self.gasket_in_slot_distance
        )

    @property
    def gasket_slot_inner_width(self) -> float:
        return (
            self.box_outer_width
            - self.wall_thickness
            - self.gasket_width
            - self.gasket_in_slot_distance
        )

    @property
    def gasket_slot_inner_length(self) -> float:
        return (
            self.box_outer_length
            - self.wall_thickness
            - self.gasket_width
            - self.gasket_in_slot_distance
        )

    @property
    def gasket_outer_width(self) -> float:
        return self.gasket_slot_outer_width - self.gasket_in_slot_distance

    @property
    def gasket_outer_length(self) -> float:
        return self.gasket_slot_outer_length - self.gasket_in_slot_distance

    @property
    def gasket_inner_width(self) -> float:
        return self.gasket_slot_inner_width + self.gasket_in_slot_distance

    @property
    def gasket_inner_length(self) -> float:
        return self.gasket_slot_inner_length + self.gasket_in_slot_distance

    @property
    def gasket_slot_width(self) -> float:
        return self.gasket_width + self.gasket_in_slot_distance

    @property
    def mount_holders_total_length(self) -> float:
        return self.box_outer_length + 2 * self.mount_holder_length

    @property
    def mount_holders_fillet_radius(self) -> float:
        return 3.0

    @property
    def gasket_slot_depth(self) -> float:
        return self.gasket_height * 2

    @property
    def gasket_press_height(self) -> float:
        return self.gasket_height * (1 + self.gasket_compression)
