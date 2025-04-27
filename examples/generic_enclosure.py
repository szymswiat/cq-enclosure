import ocp_vscode as ov
import cadquery as cq
from cq_enclosure import Enclosure, ScrewLocation, ScrewType


ov.set_port(3939)


def main():
    e = Enclosure(
        box_inner_width=31.0,
        box_inner_length=71.0,
        box_inner_height=16.0,
        screw_location=ScrewLocation.OUTSIDE_BOX,
        screw_type=ScrewType.WOOD_SCREW,
        corner_screws=False,
        middle_width_screws=True,
        middle_length_screws=False,
    )

    box, lid, gasket = e.build()

    #
    # position objects for visualization
    #

    # position lid next to box
    lid = lid.rotateAboutCenter((1, 0, 0), 180).translate(
        (e.box_outer_width + 20, 0, -(e.box_outer_height - e.cut_top))
    )

    gasket = gasket.translate((-(e.box_outer_width + 20), 0, 0))

    try:
        ov.show(
            *(box, lid, gasket),
            reset_camera=ov.Camera.KEEP,
            colors=["#004400", "#880000", "#000088"],
            black_edges=True,
        )
    finally:
        cq.exporters.export(box, "enclosure_box.step")
        cq.exporters.export(lid, "enclosure_lid.step")
        cq.exporters.export(gasket, "enclosure_gasket.step")


if __name__ == "__main__":
    main()
