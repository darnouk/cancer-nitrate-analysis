import geopandas as gpd
import numpy as np
from .hexbin import perform_hexbin_idw_interpolation, aggregate_cancer_data_to_hexbins, aggregate_cancer_data_to_hexbins_optimized, prepare_hexbin_regression_data, hexbins_to_geojson

def idw_interpolation(geojson_path, k=2, grid_res=20):
    print("[IDW DEBUG] idw_interpolation() function called.")

    wells = gpd.read_file(geojson_path)
    print(f"[IDW DEBUG] Loaded {len(wells)} wells.")

    if 'nitr_ran' not in wells.columns:
        raise ValueError("GeoJSON must have a 'nitr_ran' field.")

    # Remove wells with missing geometry or missing nitrate value
    wells = wells.dropna(subset=['geometry', 'nitr_ran'])
    wells = wells[wells.geometry.type == 'Point']
    print(f"[IDW DEBUG] Filtered to {len(wells)} valid point wells.")

    minx, miny, maxx, maxy = wells.total_bounds
    x_coords = np.linspace(minx, maxx, grid_res)
    y_coords = np.linspace(miny, maxy, grid_res)
    grid_points = [(x, y) for y in y_coords for x in x_coords]

    interpolated = []

    for index, (gx, gy) in enumerate(grid_points):
        numerator = 0
        denominator = 0
        for i, well in wells.iterrows():
            wx, wy = well.geometry.x, well.geometry.y
            dist = np.hypot(gx - wx, gy - wy)

            if dist == 0:
                z = well['nitr_ran']
                break
            else:
                weight = 1 / (dist ** k)
                numerator += weight * well['nitr_ran']
                denominator += weight
        else:
            z = numerator / denominator if denominator != 0 else 0

        interpolated.append({
            "x": float(gx),
            "y": float(gy),
            "nitrate": float(z)
        })

        if index < 5:
            print(f"[DEBUG] Point {index}: x={gx}, y={gy}, nitrate={z}")

    print(f"[IDW DEBUG] Interpolated {len(interpolated)} points.")
    return interpolated

def idw_interpolation_at_points(geojson_path, points, k=2):
    """
    Perform IDW interpolation at specific points.
    
    Args:
        geojson_path (str): Path to well nitrate GeoJSON file
        points (list): List of (x, y) coordinate tuples
        k (float): IDW distance decay coefficient
    
    Returns:
        list: Interpolated nitrate values at each point
    """
    print(f"[IDW DEBUG] idw_interpolation_at_points() called for {len(points)} points with k={k}")

    wells = gpd.read_file(geojson_path)
    print(f"[IDW DEBUG] Loaded {len(wells)} wells.")

    if 'nitr_ran' not in wells.columns:
        raise ValueError("GeoJSON must have a 'nitr_ran' field.")

    # Remove wells with missing geometry or missing nitrate value
    wells = wells.dropna(subset=['geometry', 'nitr_ran'])
    wells = wells[wells.geometry.type == 'Point']
    print(f"[IDW DEBUG] Filtered to {len(wells)} valid point wells.")

    interpolated_values = []

    for gx, gy in points:
        numerator = 0
        denominator = 0
        
        for i, well in wells.iterrows():
            wx, wy = well.geometry.x, well.geometry.y
            dist = np.hypot(gx - wx, gy - wy)
            
            if dist == 0:
                # If point is exactly at a well location, use that well's value
                interpolated_values.append(well['nitr_ran'])
                break
            else:
                weight = 1 / (dist ** k)
                numerator += weight * well['nitr_ran']
                denominator += weight
        else:
            # This executes if the loop completed without breaking
            if denominator > 0:
                interpolated_value = numerator / denominator
                interpolated_values.append(interpolated_value)
            else:
                interpolated_values.append(0)  # Default value if no wells nearby

    print(f"[IDW DEBUG] Interpolation completed. Sample values: {interpolated_values[:3] if interpolated_values else 'None'}")
    return interpolated_values

def idw_hexbin_interpolation(wells_geojson_path, cancer_geojson_path, hexbin_area=10.0, k=2.0):
    """
    Perform IDW interpolation using hexagonal bins, mimicking the reference project approach.
    
    Args:
        wells_geojson_path (str): Path to well nitrate GeoJSON file
        cancer_geojson_path (str): Path to cancer data GeoJSON file
        hexbin_area (float): Area of each hexagon in square units (like square miles)
        k (float): IDW distance decay coefficient
    
    Returns:
        dict: Dictionary containing hexbin analysis results
    """
    print(f"[HEXBIN IDW DEBUG] Starting hexbin interpolation with area={hexbin_area}, k={k}")
    
    # Load wells data
    wells_gdf = gpd.read_file(wells_geojson_path)
    print(f"[HEXBIN IDW DEBUG] Loaded {len(wells_gdf)} wells")
    
    # Load cancer data
    cancer_gdf = gpd.read_file(cancer_geojson_path)
    print(f"[HEXBIN IDW DEBUG] Loaded {len(cancer_gdf)} cancer features")
    
    # Validate wells data
    if 'nitr_ran' not in wells_gdf.columns:
        raise ValueError("Wells GeoJSON must have a 'nitr_ran' field.")
    
    # Clean wells data
    wells_gdf = wells_gdf.dropna(subset=['geometry', 'nitr_ran'])
    wells_gdf = wells_gdf[wells_gdf.geometry.type == 'Point']
    print(f"[HEXBIN IDW DEBUG] Filtered to {len(wells_gdf)} valid point wells")
    
    # Validate cancer data
    if 'canrate' not in cancer_gdf.columns:
        raise ValueError("Cancer GeoJSON must have a 'canrate' field.")
    
    # Clean cancer data
    cancer_gdf = cancer_gdf.dropna(subset=['geometry', 'canrate'])
    print(f"[HEXBIN IDW DEBUG] Filtered to {len(cancer_gdf)} valid cancer features")
    
    # Determine spatial bounds (union of both datasets)
    wells_bounds = wells_gdf.total_bounds
    cancer_bounds = cancer_gdf.total_bounds
    
    # Expand bounds to cover both datasets
    minx = min(wells_bounds[0], cancer_bounds[0])
    miny = min(wells_bounds[1], cancer_bounds[1])
    maxx = max(wells_bounds[2], cancer_bounds[2])
    maxy = max(wells_bounds[3], cancer_bounds[3])
    
    # Add some padding
    padding = 0.05 * max(maxx - minx, maxy - miny)
    bounds = (minx - padding, miny - padding, maxx + padding, maxy + padding)
    
    print(f"[HEXBIN IDW DEBUG] Using bounds: {bounds}")
    
    # Step 1: Perform IDW interpolation to hexbins for nitrate data
    print("[HEXBIN IDW DEBUG] Step 1: Interpolating nitrate data to hexbins")
    
    # Use cancer tract boundaries as study area for clipping hexagons
    study_area = cancer_gdf if cancer_gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon'] else None
    
    nitrate_hexbins = perform_hexbin_idw_interpolation(
        wells_gdf, bounds, hexbin_area, power=k, value_column='nitr_ran', study_area_gdf=study_area
    )
    print(f"[HEXBIN IDW DEBUG] Created {len(nitrate_hexbins)} nitrate hexbins")
    
    # Step 2: Aggregate cancer data to the same hexbins
    print("[HEXBIN IDW DEBUG] Step 2: Aggregating cancer data to hexbins")
    
    # If cancer data consists of polygons, we may need to convert to centroids
    # or use area-weighted aggregation (handled in the function)
    if cancer_gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
        # For polygon data, use area-weighted aggregation
        combined_hexbins = aggregate_cancer_data_to_hexbins_optimized(
            cancer_gdf, nitrate_hexbins, cancer_column='canrate'
        )
    else:
        # For point data, use centroid-based aggregation
        combined_hexbins = aggregate_cancer_data_to_hexbins_optimized(
            cancer_gdf, nitrate_hexbins, cancer_column='canrate'
        )
    
    print(f"[HEXBIN IDW DEBUG] Combined hexbins: {len(combined_hexbins)}")
    
    # Step 3: Prepare data for regression analysis
    print("[HEXBIN IDW DEBUG] Step 3: Preparing regression data")
    regression_data = prepare_hexbin_regression_data(
        combined_hexbins, 
        nitrate_column='nitr_ran_interpolated',
        cancer_column='canrate_aggregated'
    )
    
    print(f"[HEXBIN IDW DEBUG] Valid hexbins for regression: {regression_data['valid_count']}")
    
    # Step 4: Convert to GeoJSON for frontend visualization
    print("[HEXBIN IDW DEBUG] Step 4: Converting to GeoJSON")
    hexbins_geojson = hexbins_to_geojson(combined_hexbins)
    
    # Return comprehensive results
    results = {
        'hexbins_geojson': hexbins_geojson,
        'regression_data': regression_data,
        'nitrate_values': regression_data['nitrate_values'],
        'cancer_values': regression_data['cancer_values'],
        'hexbin_count': int(len(combined_hexbins)),  # Ensure it's a Python int
        'valid_hexbin_count': int(regression_data['valid_count']),  # Ensure it's a Python int
        'hexbin_area': float(hexbin_area),  # Ensure it's a Python float
        'idw_power': float(k),  # Ensure it's a Python float
        'bounds': [float(x) for x in bounds],  # Convert to list of Python floats
        'interpolation_type': 'hexbin'
    }
    
    print(f"[HEXBIN IDW DEBUG] Analysis complete. Results summary:")
    print(f"  - Total hexbins: {results['hexbin_count']}")
    print(f"  - Valid for regression: {results['valid_hexbin_count']}")
    print(f"  - Hexbin area: {hexbin_area}")
    
    return results

if __name__ == "__main__":
    result = idw_interpolation("static/data/well_nitrate.geojson", k=2, grid_res=10)
    print(result[:5])
