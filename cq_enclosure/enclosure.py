import cadquery as cq

from . import builders as bld

from .enclosure_parameters import (
    EnclosureParameters,
    ScrewType,
)


class Enclosure(EnclosureParameters):
    def build(
        self,
    ) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
        # initialize parameters
        self.initialize()

        # check parameters
        self.validate()

        (
            inner_edges_selector,
            outer_edges_selector,
            gasket_edges_selector,
        ) = bld.instantiate_selectors(self)
        screw_points = bld.compute_screw_points(self)

        box = bld.build_box(self)

        box = bld.build_screw_cylinders(self, box, screw_points)
        box = bld.create_screw_holes(self, box, screw_points)
        box = bld.fillet_box(self, box, inner_edges_selector)

        if self.screw_type == ScrewType.WITH_SQUARE_NUT:
            box = bld.create_square_nut_holes(self, box, screw_points)

        box, lid = bld.split_box(self, box)

        box = bld.create_gasket_slot(self, box, screw_points)
        lid = bld.create_gasket_press(self, lid, screw_points)
        gasket = bld.build_gasket(self, screw_points)

        box, lid, gasket = bld.apply_gasket_fillets(
            self, box, lid, gasket, gasket_edges_selector
        )

        if self.mount_holders:
            box = bld.build_mount_holders(self, box)

        return box, lid, gasket
