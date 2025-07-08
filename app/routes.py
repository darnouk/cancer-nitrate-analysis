from flask import Blueprint, render_template, request, jsonify
from app.utils.idw import idw_interpolation, idw_hexbin_interpolation
from app.utils.regression import get_correlation_summary, run_comprehensive_analysis, analyze_hexbin_regression
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

@main.route("/regression")
def regression():
    """
    Endpoint for regression analysis between nitrate levels and cancer rates.
    If k and res parameters are provided, uses IDW interpolation with those parameters.
    Returns correlation statistics and analysis results.
    """
    try:
        print("[DEBUG] /regression endpoint called")
        
        # Get IDW parameters from query string
        k = request.args.get("k", type=float)
        res = request.args.get("res", type=int)
        
        # Get analysis type from query parameter
        analysis_type = request.args.get("type", "summary")
        
        if k is not None and res is not None:
            print(f"[DEBUG] Running regression with IDW parameters: k={k}, res={res}")
            # Use IDW interpolation parameters for regression
            if analysis_type == "full":
                results = run_comprehensive_analysis(k=k, res=res)
            else:
                results = get_correlation_summary(k=k, res=res)
        else:
            print("[DEBUG] Running default regression analysis")
            # Run default analysis without IDW parameters
            if analysis_type == "full":
                results = run_comprehensive_analysis()
            else:
                results = get_correlation_summary()
        
        if 'error' in results:
            print(f"[ERROR] Regression analysis failed: {results['error']}")
            return jsonify(results), 500

        print(f"[DEBUG] Regression analysis completed successfully")
        return jsonify(results)
        
    except Exception as e:
        print(f"[ERROR] Regression endpoint failed: {e}")
        return jsonify({"error": str(e)}), 500

@main.route("/debug")
def debug():
    js_path = os.path.join(os.getcwd(), "static", "js")
    try:
        files = os.listdir(js_path)
        return f"Contents of static/js: {files}"
    except Exception as e:
        return f"Error accessing static/js: {str(e)}"

@main.route("/hexbin_analysis")
def hexbin_analysis():
    """
    Endpoint for hexbin-based analysis, mimicking the reference project approach.
    Performs IDW interpolation using hexagonal bins instead of regular grid.
    """
    try:
        print("[DEBUG] /hexbin_analysis endpoint called")
        
        # Get hexbin parameters from query string
        hexbin_area = float(request.args.get("hexbin_area", 0.1))  # Default 0.1 sq miles
        k = float(request.args.get("k", 2.0))  # IDW power parameter
        
        print(f"[DEBUG] Hexbin analysis parameters: hexbin_area={hexbin_area}, k={k}")
        
        # Validate parameters (updated ranges for smaller, more detailed hexbins)
        if hexbin_area < 0.01 or hexbin_area > 10:
            return jsonify({
                "error": "Hexbin area must be between 0.01 and 10 square miles"
            }), 400
            
        if k < 0 or k > 100:
            return jsonify({
                "error": "Distance decay coefficient must be between 0 and 100"
            }), 400
        
        # Perform hexbin analysis
        # Use absolute paths to ensure files are found regardless of working directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        wells_path = os.path.join(base_dir, "static", "data", "well_nitrate.geojson")
        cancer_path = os.path.join(base_dir, "static", "data", "cancer_tracts.geojson")
        
        print(f"[DEBUG] Wells path: {wells_path}")
        print(f"[DEBUG] Cancer path: {cancer_path}")
        print(f"[DEBUG] Wells exists: {os.path.exists(wells_path)}")
        print(f"[DEBUG] Cancer exists: {os.path.exists(cancer_path)}")
        
        if not os.path.exists(wells_path):
            return jsonify({"error": f"Wells data file not found: {wells_path}"}), 500
        if not os.path.exists(cancer_path):
            return jsonify({"error": f"Cancer data file not found: {cancer_path}"}), 500
        
        print("[DEBUG] Starting hexbin IDW interpolation...")
        hexbin_results = idw_hexbin_interpolation(
            wells_path, cancer_path, 
            hexbin_area=hexbin_area, 
            k=k
        )
        
        # Perform regression analysis on hexbin data
        print("[DEBUG] Starting hexbin regression analysis...")
        regression_results = analyze_hexbin_regression(hexbin_results['regression_data'])
        
        # Combine results
        final_results = {
            'interpolation': hexbin_results,
            'regression': regression_results,
            'parameters': {
                'hexbin_area': hexbin_area,
                'idw_power': k,
                'analysis_type': 'hexbin'
            }
        }
        
        print(f"[DEBUG] Hexbin analysis completed successfully")
        print(f"  - Hexbins created: {hexbin_results.get('hexbin_count', 0)}")
        print(f"  - Valid for regression: {hexbin_results.get('valid_hexbin_count', 0)}")
        if 'error' not in regression_results:
            print(f"  - R²: {regression_results.get('r_squared', 0):.6f}")
        
        return jsonify(final_results)
        
    except Exception as e:
        print(f"[ERROR] Hexbin analysis endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
