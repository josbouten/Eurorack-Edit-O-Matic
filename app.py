import os
import json
import importlib.util
import argparse

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    abort
)

from repository import repository
module_repository = repository

app = Flask(__name__)

# =====================================================
# DIRECTORIES
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LAYOUTS_DIR = os.path.join(BASE_DIR, "layouts")
IMAGES_DIR = os.path.join(BASE_DIR, "fotos/eurorack-modules/scaled_600")

RACK_DATA_FILE = os.path.join(BASE_DIR, "rack_data.py")

os.makedirs(LAYOUTS_DIR, exist_ok=True)


# =====================================================
# RACK CONFIGURATION
# =====================================================

RACK_HP = 84

HP_WIDTH = 12
PANEL_HEIGHT = 360

RACK_GAP = 4
RACK_MARGIN = 20


# =====================================================
# LOAD RACK_DATA.PY
# =====================================================

def load_rack_data():

    if not os.path.isfile(RACK_DATA_FILE):
        raise FileNotFoundError(
            "rack_data.py could not be found."
        )

    spec = importlib.util.spec_from_file_location(
        "rack_data",
        RACK_DATA_FILE
    )

    rack_module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(rack_module)

    # Main module configuration.
    default_modules = getattr(
        rack_module,
        "rack_data",
        getattr(rack_module, "modules", [])
    )

    return default_modules, module_repository, rack_module


rack_data, repository, rack_config = load_rack_data()


# =====================================================
# AVAILABLE LAYOUTS
# =====================================================

def get_available_layouts():

    os.makedirs(LAYOUTS_DIR, exist_ok=True)

    return sorted([

        filename

        for filename in os.listdir(LAYOUTS_DIR)

        if filename.lower().endswith(".json")

        and os.path.isfile(
            os.path.join(LAYOUTS_DIR, filename)
        )

    ])


# =====================================================
# SAFE LAYOUT PATH
# =====================================================

def get_layout_path(filename):

    if not filename.lower().endswith(".json"):
        abort(400)

    safe_filename = os.path.basename(filename)

    if safe_filename != filename:
        abort(400)

    return os.path.join(
        LAYOUTS_DIR,
        safe_filename
    )


# =====================================================
# MAIN PAGE
# =====================================================

@app.route("/")
def index():

    available_layouts = get_available_layouts()

    # Only use rack_data.py if there are no saved layouts.

    if len(available_layouts) == 0:

        initial_modules = rack_data

        use_default_layout = True

    else:

        initial_modules = []

        use_default_layout = False

    return render_template(
        "index.html",
        modules=initial_modules,
        repository=repository,
        available_layouts=available_layouts,
        use_default_layout=use_default_layout,

        rack_hp=getattr(
            rack_config,
            "rack_hp",
            RACK_HP
        ),

        rack_rows=getattr(
            rack_config,
            "rack_rows",
            RACK_ROWS
        ),

        nr_towers=getattr(
            rack_config,
            "nr_towers",
            NR_TOWERS
        ),

        hp_width=getattr(
            rack_config,
            "hp_width",
            HP_WIDTH
        ),

        panel_height=getattr(
            rack_config,
            "panel_height",
            PANEL_HEIGHT
        ),

        gap=getattr(
            rack_config,
            "gap",
            RACK_GAP
        ),

        margin=getattr(
            rack_config,
            "margin",
            RACK_MARGIN
        )

    )


# =====================================================
# IMAGE SERVING
# =====================================================

@app.route("/images/<path:filename>")
def get_image(filename):

    from flask import send_from_directory

    return send_from_directory(
        IMAGES_DIR,
        filename
    )


# =====================================================
# LIST SAVED LAYOUTS
# =====================================================

@app.route("/list_layouts")
def list_layouts():

    return jsonify(
        get_available_layouts()
    )


# =====================================================
# LOAD LAYOUT
# =====================================================

@app.route("/load_layout/<filename>")
def load_layout(filename):

    path = get_layout_path(filename)

    if not os.path.isfile(path):

        return jsonify({
            "message": "Layout not found."
        }), 404

    try:

        with open(path, "r", encoding="utf-8") as file:

            data = json.load(file)

        if isinstance(data, list):

            modules = data

        else:

            modules = data.get("modules", [])

        if not isinstance(modules, list):

            raise ValueError(
                "Invalid module configuration."
            )

        return jsonify({
            "modules": modules
        })

    except Exception as error:

        return jsonify({
            "message": str(error)
        }), 500


# =====================================================
# SAVE LAYOUT
# =====================================================

@app.route("/save_layout", methods=["POST"])
def save_layout():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "message": "No layout data received."
            }), 400

        filename = str(
            data.get("filename", "")
        ).strip()

        modules = data.get("modules", [])

        if not filename:

            return jsonify({
                "message": "Filename is required."
            }), 400

        if not filename.lower().endswith(".json"):

            filename += ".json"

        if not isinstance(modules, list):

            return jsonify({
                "message": "Invalid module data."
            }), 400

        path = get_layout_path(filename)

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "modules": modules
                },
                file,
                indent=4
            )

        return jsonify({

            "message": (
                f"Layout '{filename}' saved successfully."
            )

        })

    except Exception as error:

        return jsonify({

            "message": str(error)

        }), 500


# =====================================================
# START APPLICATION
# =====================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="eurorack-editor."
    )

    parser.add_argument(
        "--port",
        help="port for browser contact"
    )

    parser.add_argument(
        "--nr_towers",
        required=True,
        help="Number of towers 1..3"
    )

    parser.add_argument(
        "--nr_rows",
        help="Number of rows in tower"
    )

    args = parser.parse_args()

    NR_TOWERS = args.nr_towers # default 3
    RACK_ROWS = args.nr_rows # default 10
    PORT = args.port

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=True,
        threaded=True,
    )

