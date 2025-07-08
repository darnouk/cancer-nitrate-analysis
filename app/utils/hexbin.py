"""
Hexbin analysis utilities for spatial interpolation and aggregation.
This module implements true hexagonal binning using matplotlib's approach
for perfect tessellation (no overlaps, puzzle-piece fit).
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
from shapely.affinity import translate
import math
from typing import List, Tuple, Dict, Any
import json
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon


def create_hexagon_from_radius(center_x: float, center_y: float, radius: float) -> Polygon:
    """
    Create a regular hexagon polygon with flat-top orientation for proper tessellation.
    
    Args:
        center_x: X coordinate of hexagon center
        center_y: Y coordinate of hexagon center  
        radius: Radius of the hexagon (distance from center to vertex)
        
    Returns:
        Shapely Polygon representing the hexagon
    """
    # Create hexagon vertices - flat-top orientation
    # For proper tessellation, we need flat-top hexagons with vertices at specific angles
    # Starting from the right (0°) and going counter-clockwise: 0°, 60°, 120°, 180°, 240°, 300°
    angles = [i * math.pi / 3 for i in range(6)]  # 0°, 60°, 120°, 180°, 240°, 300°
    vertices = []
    
    for angle in angles:
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        vertices.append((x, y))
    
    return Polygon(vertices)


def create_hexagon(center_x: float, center_y: float, size: float) -> Polygon:
    """
    Create a regular hexagon polygon centered at the given coordinates.
    
    Args:
        center_x: X coordinate of hexagon center
        center_y: Y coordinate of hexagon center  
        size: Size parameter (relates to area)
        
    Returns:
        Shapely Polygon representing the hexagon
    """
    # Convert area to radius (approximate)
    # For a regular hexagon: Area = (3√3/2) * r²
    # So r = √(2*Area/(3√3))
    radius = math.sqrt(2 * size / (3 * math.sqrt(3)))
    
    # Create hexagon vertices
    angles = [i * math.pi / 3 for i in range(6)]  # 60-degree increments
    vertices = []
    
    for angle in angles:
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        vertices.append((x, y))
    
    return Polygon(vertices)


def generate_hexbin_grid(bounds: Tuple[float, float, float, float], 
                        hexbin_area: float) -> List[Polygon]:
    """
    Generate a hexagonal grid using matplotlib's approach for perfect tessellation.
    This ensures hexagons fit together like puzzle pieces with no overlaps.
    
    Args:
        bounds: Tuple of (minx, miny, maxx, maxy)
        hexbin_area: Area of each hexagon in square units
        
    Returns:
        List of hexagon polygons that tessellate perfectly
    """
    minx, miny, maxx, maxy = bounds
    
    # Calculate radius from desired area
    # For regular hexagon: Area = (3√3/2) * r²
    radius = math.sqrt(2 * hexbin_area / (3 * math.sqrt(3)))
    
    # Use matplotlib's hexbin spacing algorithm for perfect tessellation
    # This is the key to making hexagons fit together perfectly
    xsize = 3.0 * radius / 2.0  # Horizontal spacing between centers
    ysize = radius * math.sqrt(3)  # Vertical spacing between centers
    
    # Calculate the extent we need to cover
    width = maxx - minx
    height = maxy - miny
    
    # Number of hexagons in each direction (with buffer for edge coverage)
    nx = int(np.ceil(width / xsize)) + 2
    ny = int(np.ceil(height / ysize)) + 2
    
    print(f"[HEXBIN] Area: {hexbin_area:.3f}, Radius: {radius:.6f}")
    print(f"[HEXBIN] Grid spacing - X: {xsize:.6f}, Y: {ysize:.6f}")
    print(f"[HEXBIN] Grid size: {nx} x {ny} = {nx * ny} hexagons")
    
    # Safety check
    if nx * ny > 3000:
        print(f"[HEXBIN WARNING] Too many hexagons ({nx * ny}), reducing density")
        new_area = hexbin_area * 1.5
        return generate_hexbin_grid(bounds, new_area)
    
    hexagons = []
    
    # Generate hexagon centers using matplotlib's algorithm
    for i in range(nx):
        for j in range(ny):
            # Calculate center position
            x = minx - xsize + i * xsize
            y = miny - ysize + j * ysize
            
            # Offset every other column for hexagonal packing
            if i % 2 == 1:
                y += ysize / 2.0
            
            # Create hexagon with flat-top orientation (0 rotation)
            hexagon = create_matplotlib_hexagon(x, y, radius)
            hexagons.append(hexagon)
    
    print(f"[HEXBIN] Generated {len(hexagons)} hexagons")
    return hexagons


def create_matplotlib_hexagon(center_x: float, center_y: float, radius: float) -> Polygon:
    """
    Create a hexagon using matplotlib's approach for perfect tessellation.
    Uses flat-top orientation (0 degrees rotation).
    
    Args:
        center_x: X coordinate of center
        center_y: Y coordinate of center
        radius: Radius (center to vertex distance)
        
    Returns:
        Shapely Polygon representing the hexagon
    """
    # Create hexagon vertices using matplotlib's approach
    # Flat-top orientation means first vertex is at angle 0 (rightmost point)
    angles = np.array([0, 60, 120, 180, 240, 300]) * np.pi / 180.0
    
    vertices = []
    for angle in angles:
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        vertices.append((x, y))
    
    return Polygon(vertices)


def aggregate_points_to_hexbins(points_gdf: gpd.GeoDataFrame, 
                               hexagons: List[Polygon],
                               value_column: str,
                               aggregation_method: str = 'mean') -> gpd.GeoDataFrame:
    """
    Aggregate point data to hexagonal bins.
    
    Args:
        points_gdf: GeoDataFrame containing point data
        hexagons: List of hexagon polygons
        value_column: Column name to aggregate
        aggregation_method: Method for aggregation ('mean', 'sum', 'count')
        
    Returns:
        GeoDataFrame with hexagons and aggregated values
    """
    hexbin_data = []
    
    for i, hexagon in enumerate(hexagons):
        # Find points within this hexagon
        intersecting_points = points_gdf[points_gdf.geometry.within(hexagon)]
        
        if len(intersecting_points) > 0:
            if aggregation_method == 'mean':
                agg_value = intersecting_points[value_column].mean()
            elif aggregation_method == 'sum':
                agg_value = intersecting_points[value_column].sum()
            elif aggregation_method == 'count':
                agg_value = len(intersecting_points)
            else:
                agg_value = intersecting_points[value_column].mean()
                
            hexbin_data.append({
                'geometry': hexagon,
                'hexbin_id': i,
                f'{value_column}_{aggregation_method}': agg_value,
                'point_count': len(intersecting_points)
            })
    
    # Create GeoDataFrame
    if hexbin_data:
        hexbins_gdf = gpd.GeoDataFrame(hexbin_data)
        return hexbins_gdf
    else:
        # Return empty GeoDataFrame with correct columns
        columns = ['geometry', 'hexbin_id', f'{value_column}_{aggregation_method}', 'point_count']
        return gpd.GeoDataFrame(columns=columns)


def perform_hexbin_idw_interpolation(wells_gdf: gpd.GeoDataFrame,
                                    bounds: Tuple[float, float, float, float],
                                    hexbin_area: float,
                                    power: float = 2.0,
                                    value_column: str = 'nitr_ran',
                                    study_area_gdf: gpd.GeoDataFrame = None) -> gpd.GeoDataFrame:
    """
    Perform IDW interpolation using hexagonal bins as interpolation targets.
    
    Args:
        wells_gdf: GeoDataFrame containing well point data
        bounds: Spatial bounds for the hexbin grid
        hexbin_area: Area of each hexagon in square miles
        power: IDW power parameter
        value_column: Column containing values to interpolate
        study_area_gdf: Optional GeoDataFrame containing study area for clipping hexagons
        
    Returns:
        GeoDataFrame with hexagons and interpolated values
    """
    print(f"[HEXBIN DEBUG] Starting IDW interpolation with {hexbin_area} sq mi hexbins")
    
    # Convert hexbin area from square miles to coordinate system units
    crs_str = str(wells_gdf.crs) if wells_gdf.crs else 'EPSG:4269'
    hexbin_area_crs = convert_square_miles_to_crs_units(hexbin_area, crs_str)
    
    print(f"[HEXBIN DEBUG] Converted {hexbin_area} sq mi to {hexbin_area_crs:.8f} CRS units ({crs_str})")
    
    # Generate hexbin grid
    hexagons = generate_hexbin_grid(bounds, hexbin_area_crs)
    
    # Clip hexagons to study area if provided
    if study_area_gdf is not None:
        hexagons = clip_hexagons_to_study_area(hexagons, study_area_gdf)
    
    # Create hexbin centers for interpolation
    hexbin_centers = [hexagon.centroid for hexagon in hexagons]
    
    # Prepare well coordinates and values
    well_coords = np.array([(geom.x, geom.y) for geom in wells_gdf.geometry])
    well_values = wells_gdf[value_column].values
    
    interpolated_values = []
    
    print(f"[HEXBIN DEBUG] Performing IDW interpolation for {len(hexbin_centers)} hexbin centers")
    
    # Perform IDW for each hexbin center
    for center in hexbin_centers:
        center_coord = np.array([center.x, center.y])
        
        # Calculate distances from center to all wells
        distances = np.sqrt(np.sum((well_coords - center_coord) ** 2, axis=1))
        
        # Avoid division by zero
        distances = np.maximum(distances, 1e-10)
        
        # Calculate weights
        weights = 1.0 / (distances ** power)
        
        # Calculate IDW value
        idw_value = np.sum(weights * well_values) / np.sum(weights)
        interpolated_values.append(idw_value)
    
    # Create result GeoDataFrame
    hexbin_data = []
    for i, (hexagon, value) in enumerate(zip(hexagons, interpolated_values)):
        # Calculate actual area of hexagon (may be clipped)
        actual_area = hexagon.area
        actual_area_sq_miles = actual_area / convert_square_miles_to_crs_units(1.0, crs_str)
        
        hexbin_data.append({
            'geometry': hexagon,
            'hexbin_id': i,
            f'{value_column}_interpolated': value,
            'hexbin_area_sq_miles': actual_area_sq_miles,
            'hexbin_area_crs_units': actual_area
        })
    
    result_gdf = gpd.GeoDataFrame(hexbin_data)
    
    print(f"[HEXBIN DEBUG] IDW interpolation completed for {len(result_gdf)} hexbins")
    return result_gdf


def aggregate_cancer_data_to_hexbins(cancer_gdf: gpd.GeoDataFrame,
                                    hexbins_gdf: gpd.GeoDataFrame,
                                    cancer_column: str = 'canrate') -> gpd.GeoDataFrame:
    """
    Aggregate cancer rate data from census tracts to hexbins.
    This mimics the turf.collect() functionality from the reference project.
    
    Args:
        cancer_gdf: GeoDataFrame containing cancer rate data (polygons or centroids)
        hexbins_gdf: GeoDataFrame containing hexbin polygons
        cancer_column: Column name containing cancer rates
        
    Returns:
        Updated hexbins GeoDataFrame with cancer rate data
    """
    # Create copy of hexbins to avoid modifying original
    result_gdf = hexbins_gdf.copy()
    
    # Initialize cancer rate column
    result_gdf[f'{cancer_column}_aggregated'] = np.nan
    result_gdf['cancer_point_count'] = 0
    
    # For each hexbin, find intersecting cancer data
    for idx, hexbin_row in result_gdf.iterrows():
        hexbin_geom = hexbin_row.geometry
        
        # Find cancer features that intersect with this hexbin
        intersecting_cancer = cancer_gdf[cancer_gdf.geometry.intersects(hexbin_geom)]
        
        if len(intersecting_cancer) > 0:
            # Calculate area-weighted average if dealing with polygons
            if intersecting_cancer.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
                total_weighted_value = 0
                total_weight = 0
                
                for _, cancer_row in intersecting_cancer.iterrows():
                    intersection = cancer_row.geometry.intersection(hexbin_geom)
                    if intersection.area > 0:
                        weight = intersection.area / cancer_row.geometry.area
                        total_weighted_value += cancer_row[cancer_column] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    aggregated_value = total_weighted_value / total_weight
                else:
                    aggregated_value = intersecting_cancer[cancer_column].mean()
            else:
                # For points, just take the mean
                aggregated_value = intersecting_cancer[cancer_column].mean()
            
            result_gdf.at[idx, f'{cancer_column}_aggregated'] = aggregated_value
            result_gdf.at[idx, 'cancer_point_count'] = len(intersecting_cancer)
    
    return result_gdf


def aggregate_cancer_data_to_hexbins_optimized(cancer_gdf: gpd.GeoDataFrame,
                                               hexbins_gdf: gpd.GeoDataFrame,
                                               cancer_column: str = 'canrate') -> gpd.GeoDataFrame:
    """
    Optimized version of aggregate_cancer_data_to_hexbins using spatial indexing.
    Much faster for large datasets.
    
    Args:
        cancer_gdf: GeoDataFrame containing cancer rate data (polygons or centroids)
        hexbins_gdf: GeoDataFrame containing hexbin polygons
        cancer_column: Column name containing cancer rates
        
    Returns:
        Updated hexbins GeoDataFrame with cancer rate data
    """
    print(f"[HEXBIN DEBUG] Starting optimized cancer aggregation for {len(hexbins_gdf)} hexbins and {len(cancer_gdf)} cancer features")
    
    # Create copy of hexbins to avoid modifying original
    result_gdf = hexbins_gdf.copy()
    
    # Initialize cancer rate column
    result_gdf[f'{cancer_column}_aggregated'] = np.nan
    result_gdf['cancer_point_count'] = 0
    
    # Use spatial join for much better performance
    # This leverages spatial indexing automatically
    try:
        # Ensure both GeoDataFrames have the same CRS
        if hexbins_gdf.crs != cancer_gdf.crs:
            if hexbins_gdf.crs is None:
                hexbins_gdf = hexbins_gdf.set_crs(cancer_gdf.crs)
            elif cancer_gdf.crs is None:
                cancer_gdf = cancer_gdf.set_crs(hexbins_gdf.crs)
            else:
                # Reproject cancer data to match hexbins
                cancer_gdf = cancer_gdf.to_crs(hexbins_gdf.crs)
        
        # Perform spatial join to find intersections
        joined = gpd.sjoin(hexbins_gdf, cancer_gdf, how='left', predicate='intersects')
        
        # Group by hexbin index and aggregate cancer rates
        if len(joined) > 0:
            # Calculate mean cancer rate for each hexbin
            aggregated = joined.groupby(joined.index).agg({
                cancer_column: 'mean',
                'index_right': 'count'  # Count of intersecting cancer features
            }).rename(columns={
                cancer_column: f'{cancer_column}_aggregated',
                'index_right': 'cancer_point_count'
            })
            
            # Update result with aggregated values
            for idx in aggregated.index:
                if idx in result_gdf.index:
                    result_gdf.at[idx, f'{cancer_column}_aggregated'] = aggregated.at[idx, f'{cancer_column}_aggregated']
                    result_gdf.at[idx, 'cancer_point_count'] = aggregated.at[idx, 'cancer_point_count']
        
        print(f"[HEXBIN DEBUG] Cancer aggregation completed. {len(result_gdf.dropna(subset=[f'{cancer_column}_aggregated']))} hexbins have cancer data")
        
    except Exception as e:
        print(f"[HEXBIN DEBUG] Error in optimized aggregation, falling back to original method: {e}")
        return aggregate_cancer_data_to_hexbins(cancer_gdf, hexbins_gdf, cancer_column)
    
    return result_gdf


def prepare_hexbin_regression_data(hexbins_gdf: gpd.GeoDataFrame,
                                  nitrate_column: str = 'nitr_ran_interpolated',
                                  cancer_column: str = 'canrate_aggregated') -> Dict[str, Any]:
    """
    Prepare hexbin data for regression analysis.
    
    Args:
        hexbins_gdf: GeoDataFrame containing hexbins with both nitrate and cancer data
        nitrate_column: Column name for nitrate values
        cancer_column: Column name for cancer rate values
        
    Returns:
        Dictionary containing regression-ready data and metadata
    """
    # Filter out hexbins with missing data
    valid_hexbins = hexbins_gdf.dropna(subset=[nitrate_column, cancer_column])
    
    if len(valid_hexbins) == 0:
        return {
            'nitrate_values': [],
            'cancer_values': [],
            'hexbin_ids': [],
            'valid_count': 0,
            'total_count': len(hexbins_gdf)
        }
    
    return {
        'nitrate_values': valid_hexbins[nitrate_column].tolist(),
        'cancer_values': valid_hexbins[cancer_column].tolist(),
        'hexbin_ids': valid_hexbins['hexbin_id'].tolist(),
        'valid_count': len(valid_hexbins),
        'total_count': len(hexbins_gdf)
        # Removed 'hexbins_gdf': valid_hexbins - GeoDataFrames are not JSON serializable
    }


def hexbins_to_geojson(hexbins_gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    Convert hexbins GeoDataFrame to GeoJSON dictionary for frontend visualization.
    
    Args:
        hexbins_gdf: GeoDataFrame containing hexbin data
        
    Returns:
        GeoJSON dictionary (not string)
    """
    # Set CRS if not already set
    if hexbins_gdf.crs is None:
        print("[HEXBIN DEBUG] Setting CRS to EPSG:4269 for hexbins")
        hexbins_gdf = hexbins_gdf.set_crs('EPSG:4269')
    
    # Ensure CRS is WGS84 for web display
    if hexbins_gdf.crs != 'EPSG:4326':
        hexbins_gdf = hexbins_gdf.to_crs('EPSG:4326')
    
    # Convert to GeoJSON dictionary (not string)
    import json
    geojson_str = hexbins_gdf.to_json()
    geojson_dict = json.loads(geojson_str)  # Convert string back to dict
    
    return geojson_dict


def clip_hexagons_to_study_area(hexagons: List[Polygon], 
                               study_area_gdf: gpd.GeoDataFrame) -> List[Polygon]:
    """
    Clip hexagons to the study area boundary to prevent them from extending
    beyond the region of interest.
    
    Args:
        hexagons: List of hexagon polygons
        study_area_gdf: GeoDataFrame containing the study area boundary
        
    Returns:
        List of clipped hexagon polygons that intersect with the study area
    """
    print(f"[HEXBIN] Clipping {len(hexagons)} hexagons to study area")
    
    # Get the union of all study area geometries
    study_area_union = study_area_gdf.unary_union
    
    clipped_hexagons = []
    for hexagon in hexagons:
        # Check if hexagon intersects with study area
        if hexagon.intersects(study_area_union):
            # Clip hexagon to study area boundary
            clipped = hexagon.intersection(study_area_union)
            
            # Only keep if the clipped result is a meaningful polygon
            if hasattr(clipped, 'geom_type'):
                if clipped.geom_type == 'Polygon' and clipped.area > 0:
                    clipped_hexagons.append(clipped)
                elif clipped.geom_type == 'MultiPolygon':
                    # Add all polygon parts if it's a MultiPolygon
                    for poly in clipped.geoms:
                        if poly.area > 0:
                            clipped_hexagons.append(poly)
    
    print(f"[HEXBIN] Clipped to {len(clipped_hexagons)} hexagons within study area")
    return clipped_hexagons


def convert_square_miles_to_crs_units(area_sq_miles: float, crs: str) -> float:
    """
    Convert area from square miles to coordinate system units.
    
    Args:
        area_sq_miles: Area in square miles
        crs: Coordinate reference system string (e.g., 'EPSG:4269')
        
    Returns:
        Area in CRS units
    """
    # For geographic coordinate systems (degrees), we need to convert differently
    # For projected coordinate systems (meters/feet), conversion is more straightforward
    
    if crs in ['EPSG:4326', 'EPSG:4269']:  # Geographic (WGS84, NAD83)
        # Approximate conversion for mid-latitudes in US
        # 1 square mile ≈ 0.000247105 square degrees at ~45° latitude
        # This is an approximation - ideally we'd use the actual study area centroid
        sq_miles_to_sq_degrees = 0.000247105
        return area_sq_miles * sq_miles_to_sq_degrees
    else:
        # For projected coordinate systems, assume meters
        # 1 square mile = 2,589,988.11 square meters
        sq_miles_to_sq_meters = 2589988.11
        return area_sq_miles * sq_miles_to_sq_meters
