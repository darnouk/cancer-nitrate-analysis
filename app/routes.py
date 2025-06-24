from flask import Blueprint, render_template, request, jsonify
from app.utils.idw import idw_interpolation
import os

main = Blueprint('main', __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/interpolate")
def interpolate():
    try:
        k = float(request.args.get("k", 2))
        grid_res = int(request.args.get("res", 5))  # <-- drastically reduced
        print(f"[DEBUG] /interpolate requested with k={k}, grid_res={grid_res}")

        data = idw_interpolation("static/data/well_nitrate.geojson", k=k, grid_res=grid_res)
        
        print(f"[DEBUG] Interpolation completed. Returned {len(data)} points.")
        if data:
            print("First 3 points:", data[:3])
        else:
            print("[DEBUG] No data returned from interpolation.")

        return jsonify(data)
    except Exception as e:
        print(f"[ERROR] Interpolation failed: {e}")
        return jsonify({"error": str(e)}), 500


@main.route("/debug")
def debug():
    js_path = os.path.join(os.getcwd(), "static", "js")
    try:
        files = os.listdir(js_path)
        return f"Contents of static/js: {files}"
    except Exception as e:
        return f"Error accessing static/js: {str(e)}"
