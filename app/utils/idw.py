import geopandas as gpd
import numpy as np

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

if __name__ == "__main__":
    result = idw_interpolation("static/data/well_nitrate.geojson", k=2, grid_res=10)
    print(result[:5])
