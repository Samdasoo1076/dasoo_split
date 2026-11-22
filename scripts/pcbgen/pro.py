"""Write the .kicad_pro project file next to a board."""
import json
import os


def write_project(board, pcb_path, title, root=None):
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {},
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "meta": {"version": 2},
                "rule_severities": {},
                "rules": {
                    "max_error": 0.005,
                    "min_clearance": 0.2,
                    "min_connection": 0,
                    "min_copper_edge_clearance": 0.3,
                    "min_hole_clearance": 0.2,
                    "min_through_hole_diameter": 0.3,
                    "min_track_width": 0.25,
                    "min_via_annular_width": 0.1,
                    "min_via_diameter": 0.6,
                    "solder_mask_clearance": 0.0,
                    "solder_mask_min_width": 0.0,
                },
                "track_widths": [0.0, 0.25, 0.5],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": 0.6, "drill": 0.3}],
                "zones_allow_external_fillets": False,
            },
            "layer_presets": [],
            "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": os.path.basename(pcb_path).replace(".kicad_pcb", ".kicad_pro"),
                 "version": 1},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.2, "track_width": 0.25,
                 "via_diameter": 0.6, "via_drill": 0.3,
                 "wire_width": 6, "bus_width": 12, "line_style": 0,
                 "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)"}
            ],
            "meta": {"version": 3},
        },
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "",
                                 "specctra_dsn": "", "step": "", "vrml": ""},
                   "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[root or "", "Root"]],
        "text_variables": {},
    }
    path = pcb_path.replace(".kicad_pcb", ".kicad_pro")
    with open(path, "w") as f:
        json.dump(pro, f, indent=2)
    return path
