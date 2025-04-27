import cadquery as cq

from .enclosure_parameters import (
    EnclosureParameters,
    ScrewLocation,
    NutPrintingWA,
    ScrewType,
)


def build_box(p: EnclosureParameters) -> cq.Workplane:
    # create box using outer dimensions
    box = (
        cq.Workplane("XY")
        .rect(p.box_outer_width, p.box_outer_length)
        .extrude(p.box_outer_height)
    )

    # cut inner space in box
    box = (
        box.faces("<Z")
        .workplane(invert=True, offset=p.bottom_and_lid_thickness)
        .rect(p.box_inner_width, p.box_inner_length)
        .cutBlind(p.box_inner_height)
    )

    return box


def compute_screw_points(p: EnclosureParameters) -> list[tuple[float, float]]:
    match p.screw_location:
        case ScrewLocation.INSIDE_BOX:
            screw_width_loc = (
                p.box_inner_width / 2 - p.screw_cylinder_radius + p.wall_thickness
            )
            screw_lenght_loc = (
                p.box_inner_length / 2 - p.screw_cylinder_radius + p.wall_thickness
            )
        case ScrewLocation.OUTSIDE_BOX:
            screw_width_loc = (
                p.box_outer_width / 2 + p.screw_cylinder_radius - p.wall_thickness
            )
            screw_lenght_loc = (
                p.box_outer_length / 2 + p.screw_cylinder_radius - p.wall_thickness
            )
        case _:
            raise ValueError("Invalid screws location.")

    # create a list with screw points
    screw_points = []
    if p.corner_screws:
        screw_points.extend(
            (
                (screw_width_loc, screw_lenght_loc),
                (-screw_width_loc, -screw_lenght_loc),
                (screw_width_loc, -screw_lenght_loc),
                (-screw_width_loc, screw_lenght_loc),
            )
        )

    # add additional screw points along X axis
    if p.middle_length_screws:
        screw_points.extend(((-screw_width_loc, 0), (screw_width_loc, 0)))

    # add additional screw points along Y axis
    if p.middle_width_screws:
        screw_points.extend(((0, -screw_lenght_loc), (0, screw_lenght_loc)))

    return screw_points


def build_screw_cylinders(
    p: EnclosureParameters,
    box: cq.Workplane,
    screw_points: list[tuple[float, float]],
) -> cq.Workplane:
    # add base screw cylinders
    box = (
        box.faces(">Z")
        .workplane(invert=True)
        .pushPoints(screw_points)
        .circle(p.screw_cylinder_radius)
        .extrude(p.box_outer_height)
    )

    return box


def instantiate_selectors(p: EnclosureParameters):
    # create inner edges selector
    inner_edges_selector = cq.selectors.BoxSelector(
        (-p.box_inner_width / 2 - 1, -p.box_inner_length / 2 - 1, -1),
        (p.box_inner_width / 2 + 1, p.box_inner_length / 2 + 1, p.box_inner_height + 1),
    )

    # create outer edges selector
    outer_edges_selector = cq.selectors.BoxSelector(
        (-p.box_outer_width / 2 - 1e-3, -p.box_outer_length / 2 - 1e-3, -1),
        (
            p.box_outer_width / 2 + 1e-3,
            p.box_outer_length / 2 + 1e-3,
            p.box_inner_height + 1,
        ),
    )
    outer_edges_selector = cq.selectors.InverseSelector(outer_edges_selector)

    # setup gasket edges selector
    gasket_edges_selector_outer = cq.selectors.BoxSelector(
        (
            p.box_outer_width / 2 - 1e-3,
            p.box_outer_length / 2 - 1e-3,
            p.box_outer_height - p.cut_top - p.gasket_height * 2,
        ),
        (
            -p.box_outer_width / 2 + 1e-3,
            -p.box_outer_length / 2 + 1e-3,
            p.box_outer_height - p.cut_top + p.gasket_height * 2,
        ),
    )

    gasket_edges_selector_inner = cq.selectors.BoxSelector(
        (
            p.box_inner_width / 2 + 1e-3,
            p.box_inner_length / 2 + 1e-3,
            p.box_outer_height - p.cut_top - p.gasket_height * 2,
        ),
        (
            -p.box_inner_width / 2 - 1e-3,
            -p.box_inner_length / 2 - 1e-3,
            p.box_outer_height - p.cut_top + p.gasket_height * 2,
        ),
    )

    gasket_edges_selector = cq.selectors.SubtractSelector(
        gasket_edges_selector_outer, gasket_edges_selector_inner
    )

    return (
        inner_edges_selector,
        outer_edges_selector,
        gasket_edges_selector,
    )


def fillet_box(
    p: EnclosureParameters,
    box: cq.Workplane,
    inner_edges_selector: cq.Selector,
) -> cq.Workplane:
    match p.screw_location:
        case ScrewLocation.OUTSIDE_BOX:
            # fillet screw hole cylinders
            box = box.edges(
                cq.selectors.SubtractSelector(
                    cq.StringSyntaxSelector("|Z"), inner_edges_selector
                )
            ).fillet(p.screw_cylinder_fillet)

            # fillet inner edges
            box = box.edges("|Z").edges(inner_edges_selector).fillet(p.inner_fillet)
        case ScrewLocation.INSIDE_BOX:
            # fillet screw hole cylinders
            box = (
                box.edges("|Z")
                .edges(inner_edges_selector)
                .fillet(p.screw_cylinder_fillet)
            )

            # fillet outer vertical edges
            box = box.edges(
                cq.selectors.SubtractSelector(
                    cq.StringSyntaxSelector("|Z"), inner_edges_selector
                )
            ).fillet(p.outer_vertical_edges_fillet)
        case _:
            raise ValueError("Invalid screws location.")

    if p.fillet_top:
        # fillet top of the lid
        box = (
            box.faces(">Z")
            .edges(cq.selectors.InverseSelector(cq.selectors.TypeSelector("CIRCLE")))
            .fillet(p.bottom_lid_fillet - 1e-2)
        )

    if p.fillet_bottom and p.mount_holders is False:
        # fillet bottom of the box
        box = box.faces("<Z").fillet(p.bottom_lid_fillet)

    return box


def create_screw_holes(
    p: EnclosureParameters,
    box: cq.Workplane,
    screw_points: list[tuple[float, float]],
) -> cq.Workplane:
    # create screw holes in screw cylinders
    box = (
        box.faces(">Z")
        .workplane()
        .pushPoints(screw_points)
        .cskHole(p.lid_screw_hole_diameter, p.screw_head_diameter, 82, p.cut_top)
        .pushPoints(screw_points)
        .hole(p.screw_hole_diameter, p.screw_total_length)
    )

    return box


def create_square_nut_holes(
    p: EnclosureParameters,
    box: cq.Workplane,
    screw_points: list[tuple[float, float]],
) -> cq.Workplane:
    # create square nut holes
    box = (
        box.faces(">Z")
        .workplane(offset=p.square_nut_depth_placement, invert=True)
        .tag("base_plane")
        .pushPoints(screw_points)
        .rect(p.square_nut_width, p.square_nut_width)
        .cutBlind(p.square_nut_height)
    )

    match p.nut_wa_type:
        case NutPrintingWA.CUT_RECT_SPACES:
            box = (
                box.workplaneFromTagged("base_plane")
                .workplane(invert=True)
                .pushPoints(screw_points)
                .rect(p.square_nut_width, p.screw_hole_diameter)
                .cutBlind(p.layer_height)
                .workplaneFromTagged("base_plane")
                .workplane(offset=p.layer_height, invert=True)
                .pushPoints(screw_points)
                .rect(p.screw_hole_diameter, p.screw_hole_diameter)
                .cutBlind(p.layer_height)
            )
        case NutPrintingWA.ADD_CEILING:
            box = (
                box.workplaneFromTagged("base_plane")
                .workplane(invert=True)
                .pushPoints(screw_points)
                .rect(p.square_nut_width, p.square_nut_width)
                .extrude(p.layer_height)
            )
        case _:
            raise ValueError("Invalid nut_wa_type.")

    return box


def split_box(
    p: EnclosureParameters,
    box: cq.Workplane,
) -> tuple[cq.Workplane, cq.Workplane]:
    # split model into box and lid
    lid, box = (
        box.faces(">Z")
        .workplane(offset=-p.cut_top)
        .split(keepTop=True, keepBottom=True)
        .all()
    )

    return box, lid


def create_gasket_slot(
    p: EnclosureParameters,
    box: cq.Workplane,
    screw_points: list[tuple[float, float]],
) -> cq.Workplane:
    # create gasket slot in a box
    box = (
        box.faces(">Z")
        .workplane(invert=True)
        .rect(p.gasket_slot_outer_width, p.gasket_slot_outer_length)
        .rect(p.gasket_slot_inner_width, p.gasket_slot_inner_length)
        .cutBlind(p.gasket_slot_depth)
    )

    if p.screw_location == ScrewLocation.INSIDE_BOX:
        gasket_slot_hole_outer_radius = (
            p.box_screw_hole_radius
            + (p.screw_cylinder_radius - p.box_screw_hole_radius + p.gasket_slot_width)
            / 2
        )
        gasket_slot_hole_inner_radius = (
            p.box_screw_hole_radius
            + (p.screw_cylinder_radius - p.box_screw_hole_radius - p.gasket_slot_width)
            / 2
        )
        # create gasket holes around screw holes in cylinders
        box = (
            box.faces(">Z")
            .workplane(invert=True)
            .pushPoints(screw_points)
            .circle(gasket_slot_hole_outer_radius)
            .circle(gasket_slot_hole_inner_radius)
            .cutBlind(p.gasket_slot_depth)
        )

        # make sure there is a tiny space to remove between rectangular gasket slot and circular ones
        faces = box.faces(">Z").faces(cq.selectors.AreaNthSelector(0)).vals()
        if min(face.Area() for face in faces) < p.screw_hole_diameter**1.5:  # type: ignore
            box = (
                box.faces(">Z")
                .faces(cq.selectors.AreaNthSelector(0))
                .wires()
                .toPending()
                .cutBlind(p.gasket_slot_depth)
            )

    return box


def create_gasket_press(
    p: EnclosureParameters,
    lid: cq.Workplane,
    screw_points: list[tuple[float, float]],
) -> cq.Workplane:
    # create gasket press on a lid
    lid = (
        lid.faces("<Z")
        .workplane()
        .tag("base_plane")
        .rect(p.gasket_outer_width, p.gasket_outer_length)
        .rect(p.gasket_inner_width, p.gasket_inner_length)
        .extrude(p.gasket_press_height)
    )

    if p.screw_location == ScrewLocation.INSIDE_BOX:
        # create gasket press around holes
        lid = (
            lid.workplaneFromTagged("base_plane")
            .pushPoints(screw_points)
            .circle(
                p.box_screw_hole_radius
                + (p.screw_cylinder_radius - p.box_screw_hole_radius + p.gasket_width)
                / 2
            )
            .circle(
                p.box_screw_hole_radius
                + (p.screw_cylinder_radius - p.box_screw_hole_radius - p.gasket_width)
                / 2
            )
            .extrude(p.gasket_press_height)
        )
        # fill space remaining between gasket press around holes and rectangular one
        # make sure there is a tiny space to remove between rectangular gasket slot and circular ones
        # check area of all faces due to cadquery non-deterministic buggy behaviour
        if (
            min(face.Area() for face in lid.faces("<Z[2]").vals())  # type: ignore
            < p.screw_hole_diameter**1.5
        ):
            lid = (
                lid.faces("<Z[2]")
                .wires(cq.selectors.LengthNthSelector(0))
                .toPending()
                .extrude(p.gasket_press_height)
            )

    return lid


def build_gasket(
    p: EnclosureParameters, screw_points: list[tuple[float, float]]
) -> cq.Workplane:
    # create gasket
    gasket = (
        cq.Workplane("XY")
        .rect(p.gasket_outer_width, p.gasket_outer_length)
        .rect(p.gasket_inner_width, p.gasket_inner_length)
        .extrude(p.gasket_height)
    )

    if p.screw_location == ScrewLocation.INSIDE_BOX:
        # create gasket around holes
        gasket = (
            gasket.faces("<Z")
            .workplane(invert=True)
            .pushPoints(screw_points)
            .circle(
                p.box_screw_hole_radius
                + (p.screw_cylinder_radius - p.box_screw_hole_radius + p.gasket_width)
                / 2
            )
            .circle(
                p.box_screw_hole_radius
                + (p.screw_cylinder_radius - p.box_screw_hole_radius - p.gasket_width)
                / 2
            )
            .extrude(p.gasket_height)
        )

        min_wire_len = min(
            sum(edge.Length() for edge in wire)  # type: ignore
            for wire in gasket.faces("<Z")
            .wires(cq.selectors.LengthNthSelector(0))
            .vals()
        )
        if min_wire_len < p.screw_hole_diameter**1.5:  # type: ignore
            gasket = (
                gasket.faces("<Z")
                .wires(cq.selectors.LengthNthSelector(0))
                .toPending()
                .extrude(p.gasket_height)
            )

    return gasket


def apply_gasket_fillets(
    p: EnclosureParameters,
    box: cq.Workplane,
    lid: cq.Workplane,
    gasket: cq.Workplane,
    gasket_edges_selector: cq.Selector,
) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    # fillet gasket slot
    box = box.edges("|Z").edges(gasket_edges_selector).fillet(p.gasket_fillet)
    # fillet gasket press
    lid = lid.edges("|Z").edges(gasket_edges_selector).fillet(p.gasket_fillet)
    # fillet gasket
    gasket = gasket.edges("|Z").fillet(p.gasket_fillet)

    return box, lid, gasket


def build_mount_holders(
    p: EnclosureParameters,
    box: cq.Workplane,
) -> cq.Workplane:
    # create holder base
    box = (
        box.faces("<Z")
        .workplane(invert=True)
        .rect(p.box_outer_width / 2, p.mount_holders_total_length)
        .extrude(p.bottom_and_lid_thickness)
    )

    # create holder selector
    mount_holder_selector = cq.selectors.BoxSelector(
        (-p.box_outer_width / 4 - 1, -(p.mount_holders_total_length) / 2 - 1, -1),
        (
            p.box_outer_width / 4 + 1,
            p.mount_holders_total_length / 2 + 1,
            p.bottom_and_lid_thickness + 1,
        ),
    )

    if p.mount_holders_fillet:
        # fillet holder edges
        box = (
            box.edges("|Z")
            .edges(mount_holder_selector)
            .fillet(p.mount_holders_fillet_radius)
        )

    # fillet bottom of the box
    box = box.faces("<Z").fillet(p.bottom_lid_fillet)

    # create holder screw holes
    outer_len_with_cylinders = p.box_outer_length
    if p.middle_width_screws and p.screw_location == ScrewLocation.OUTSIDE_BOX:
        screw_lenght_loc = (
            p.box_outer_length / 2 + p.screw_cylinder_radius - p.wall_thickness
        )
        outer_len_with_cylinders = (screw_lenght_loc + p.screw_cylinder_radius) * 2
        holder_holes_spread = (
            outer_len_with_cylinders
            + (p.mount_holders_total_length - outer_len_with_cylinders) / 2
        )
    else:
        holder_holes_spread = (
            p.box_outer_length + (p.mount_holders_total_length - p.box_outer_length) / 2
        )
    box = (
        box.faces("<Z[-2]")
        .workplane()
        .pushPoints(
            (
                (0, -holder_holes_spread / 2),
                (0, holder_holes_spread / 2),
            )
        )
        .cskHole(
            p.mount_holders_screw_hole_diameter,
            p.mount_holders_head_screw_diameter,
            82,
            p.bottom_and_lid_thickness,
        )
    )

    return box
