import geopandas as gpd
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import json
import os

def aggregate_nitrate_by_tracts(wells_path, tracts_path):
    """
    Aggregate nitrate measurements to census tract level using spatial join.
    
    Args:
        wells_path (str): Path to well nitrate GeoJSON file
        tracts_path (str): Path to cancer tracts GeoJSON file
    
    Returns:
        pd.DataFrame: Census tract-level aggregated data with nitrate statistics
    """
    print("[REGRESSION DEBUG] Starting nitrate aggregation by census tracts...")
    
    # Load data
    wells = gpd.read_file(wells_path)
    tracts = gpd.read_file(tracts_path)
    
    print(f"[REGRESSION DEBUG] Loaded {len(wells)} wells and {len(tracts)} census tracts")
    
    # Clean wells data
    wells = wells.dropna(subset=['geometry', 'nitr_ran'])
    wells = wells[wells.geometry.type == 'Point']
    
    # Ensure same CRS
    if wells.crs != tracts.crs:
        wells = wells.to_crs(tracts.crs)
    
    # Spatial join: assign each well to a census tract
    wells_with_tract = gpd.sjoin(wells, tracts, how='left', predicate='within')
    
    # Find the tract identifier column (could be GEOID, FIPS, etc.)
    # Check what column exists in the tracts data
    tract_id_col = None
    possible_ids = ['GEOID', 'FIPS', 'TRACT_ID', 'ID', 'FID']
    for col in possible_ids:
        if col in wells_with_tract.columns:
            tract_id_col = col
            break
    
    if tract_id_col is None:
        # Use the first non-geometry column as tract ID
        non_geom_cols = [col for col in tracts.columns if col != 'geometry']
        if non_geom_cols:
            tract_id_col = non_geom_cols[0]
        else:
            raise ValueError("Could not identify tract ID column")
    
    print(f"[REGRESSION DEBUG] Using {tract_id_col} as tract identifier")
    
    # Group by tract and calculate statistics
    tract_stats = wells_with_tract.groupby(tract_id_col).agg({
        'nitr_ran': ['mean', 'median', 'std', 'min', 'max', 'count']
    }).round(4)
    
    # Flatten MultiIndex columns properly
    if isinstance(tract_stats.columns, pd.MultiIndex):
        tract_stats.columns = [f"{col[0]}_{col[1]}" for col in tract_stats.columns]
    
    # Rename columns to more meaningful names
    column_mapping = {
        'nitr_ran_mean': 'nitrate_mean',
        'nitr_ran_median': 'nitrate_median', 
        'nitr_ran_std': 'nitrate_std',
        'nitr_ran_min': 'nitrate_min',
        'nitr_ran_max': 'nitrate_max',
        'nitr_ran_count': 'well_count'
    }
    tract_stats = tract_stats.rename(columns=column_mapping)
    
    # Merge with tract data to get cancer rates
    result = tracts.merge(tract_stats, left_on=tract_id_col, right_index=True, how='left')
    
    # Fill NaN values for tracts with no wells
    result['well_count'] = result['well_count'].fillna(0)
    for col in ['nitrate_mean', 'nitrate_median', 'nitrate_std', 'nitrate_min', 'nitrate_max']:
        result[col] = result[col].fillna(0)
    
    print(f"[REGRESSION DEBUG] Aggregated data for {len(result)} census tracts")
    print(f"[REGRESSION DEBUG] Tracts with wells: {len(result[result['well_count'] > 0])}")
    
    return result

def perform_regression_analysis(tract_data, nitrate_col='nitrate_mean', cancer_col='canrate'):
    """
    Perform linear regression analysis between nitrate levels and cancer rates.
    
    Args:
        tract_data (pd.DataFrame): Census tract-level data with nitrate and cancer columns
        nitrate_col (str): Column name for nitrate values
        cancer_col (str): Column name for cancer rates
    
    Returns:
        dict: Regression results including statistics and predictions
    """
    print(f"[REGRESSION DEBUG] Performing regression analysis: {nitrate_col} vs {cancer_col}")
    
    # Filter tracts with both nitrate and cancer data
    valid_data = tract_data.dropna(subset=[nitrate_col, cancer_col])
    valid_data = valid_data[valid_data['well_count'] > 0]  # Only tracts with wells
    
    if len(valid_data) < 3:
        return {
            'error': 'Insufficient data for regression analysis',
            'n_tracts': len(valid_data)
        }
    
    X = valid_data[nitrate_col].values.reshape(-1, 1)
    y = valid_data[cancer_col].values
    
    # Perform linear regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Make predictions
    y_pred = model.predict(X)
    
    # Calculate statistics
    r2 = r2_score(y, y_pred)
    
    # Pearson correlation
    correlation, _ = stats.pearsonr(X.flatten(), y)
    
    # Calculate residuals
    residuals = y - y_pred
    
    # Additional statistics
    mse = np.mean(residuals ** 2)
    rmse = np.sqrt(mse)
    
    # Get tract identifier for results
    tract_id_col = None
    possible_ids = ['GEOID', 'FIPS', 'TRACT_ID', 'ID', 'FID']
    for col in possible_ids:
        if col in valid_data.columns:
            tract_id_col = col
            break
    
    if tract_id_col is None:
        tract_id_col = valid_data.columns[0]  # Use first available column
    
    results = {
        'n_tracts': int(len(X)),
        'slope': float(model.coef_[0]),
        'intercept': float(model.intercept_),
        'r_squared': float(r2),
        'correlation': float(correlation),
        'rmse': float(rmse),
        'mse': float(mse),
        'equation': f"Cancer Rate = {model.intercept_:.4f} + {model.coef_[0]:.4f} * Nitrate",
        'data_points': [
            {
                'tract_id': str(getattr(row, tract_id_col)),
                'nitrate': float(getattr(row, nitrate_col)),
                'cancer_rate': float(getattr(row, cancer_col)),
                'predicted': float(pred),
                'residual': float(res)
            }
            for row, pred, res in zip(valid_data.itertuples(index=False), 
                                    y_pred, residuals)
        ]
    }
    
    print(f"[REGRESSION DEBUG] Analysis complete: R² = {r2:.4f}")
    
    return results

def run_comprehensive_analysis(wells_path="static/data/well_nitrate.geojson", 
                              tracts_path="static/data/cancer_tracts.geojson",
                              output_path="outputs/regression_results.csv",
                              k=None, res=None):
    """
    Run complete regression analysis and save results.
    
    Args:
        wells_path (str): Path to well nitrate data
        tracts_path (str): Path to cancer tracts data
        output_path (str): Path to save CSV results
        k (float): IDW distance decay coefficient (if provided, uses IDW interpolation)
        res (int): IDW grid resolution (if provided, uses IDW interpolation)
    
    Returns:
        dict: Complete analysis results
    """
    try:
        # Step 1: Aggregate nitrate data by census tracts
        if k is not None and res is not None:
            print(f"[REGRESSION DEBUG] Using IDW interpolation with k={k}, res={res}")
            tract_data = aggregate_idw_by_tracts(wells_path, tracts_path, k=k, res=res)
        else:
            print("[REGRESSION DEBUG] Using direct well aggregation")
            tract_data = aggregate_nitrate_by_tracts(wells_path, tracts_path)
        
        # Step 2: Perform regression analysis
        results = perform_regression_analysis(tract_data)
        
        if 'error' in results:
            return results
        
        # Step 3: Save detailed results to CSV
        if output_path:
            # Create DataFrame for CSV output
            df_results = pd.DataFrame(results['data_points'])
            
            # Add summary statistics as a header comment
            summary_info = [
                f"# Regression Analysis Results - Census Tract Level",
                f"# Equation: {results['equation']}",
                f"# R-squared: {results['r_squared']:.4f}",
                f"# Correlation: {results['correlation']:.4f}",
                f"# RMSE: {results['rmse']:.4f}",
                f"# Census tracts analyzed: {results['n_tracts']}",
                ""
            ]
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write summary and data
            with open(output_path, 'w') as f:
                f.write('\n'.join(summary_info))
            
            df_results.to_csv(output_path, mode='a', index=False)
            print(f"[REGRESSION DEBUG] Results saved to {output_path}")
        
        # Step 4: Add tract-level data for mapping
        tract_id_col = None
        possible_ids = ['GEOID', 'FIPS', 'TRACT_ID', 'ID', 'FID']
        for col in possible_ids:
            if col in tract_data.columns:
                tract_id_col = col
                break
        
        if tract_id_col is None:
            tract_id_col = tract_data.columns[0]
        
        results['tract_data'] = tract_data[
            [tract_id_col, 'canrate', 'nitrate_mean', 'nitrate_median', 'well_count']
        ].to_dict('records')
        
        return results
        
    except Exception as e:
        print(f"[REGRESSION ERROR] Analysis failed: {e}")
        return {'error': str(e)}

def get_correlation_summary(wells_path="static/data/well_nitrate.geojson", 
                           tracts_path="static/data/cancer_tracts.geojson",
                           k=None, res=None):
    """
    Get a quick summary of the correlation analysis.
    
    Args:
        wells_path (str): Path to well nitrate data
        tracts_path (str): Path to cancer tracts data
        k (float): IDW distance decay coefficient (if provided, uses IDW interpolation)
        res (int): IDW grid resolution (if provided, uses IDW interpolation)
    
    Returns:
        dict: Summary statistics for web display
    """
    results = run_comprehensive_analysis(wells_path, tracts_path, output_path=None, k=k, res=res)
    
    if 'error' in results:
        return results
    
    # Return simplified summary for web interface
    return {
        'correlation': float(results['correlation']),
        'r_squared': float(results['r_squared']),
        'equation': str(results['equation']),
        'n_tracts': int(results['n_tracts']),
        'interpretation': str(interpret_correlation(results['correlation']))
    }

def interpret_correlation(correlation):
    """
    Provide human-readable interpretation of correlation results.
    
    Args:
        correlation (float): Pearson correlation coefficient
    
    Returns:
        str: Interpretation text
    """
    strength = abs(correlation)
    direction = "positive" if correlation > 0 else "negative"
    
    if strength < 0.1:
        strength_desc = "negligible"
    elif strength < 0.3:
        strength_desc = "weak"
    elif strength < 0.5:
        strength_desc = "moderate"
    elif strength < 0.7:
        strength_desc = "strong"
    else:
        strength_desc = "very strong"
    
    return f"There is a {strength_desc} {direction} correlation (r = {correlation:.3f})."

def aggregate_idw_by_tracts(wells_path, tracts_path, k=2, res=20):
    """
    Use IDW interpolation to estimate nitrate values at census tract centroids.
    
    Args:
        wells_path (str): Path to well nitrate GeoJSON file
        tracts_path (str): Path to cancer tracts GeoJSON file
        k (float): IDW distance decay coefficient
        res (int): Not used for tract centroids, but kept for compatibility
    
    Returns:
        pd.DataFrame: Census tract-level data with IDW-interpolated nitrate values
    """
    print(f"[REGRESSION DEBUG] Starting IDW interpolation for census tracts with k={k}...")
    
    # Import IDW function
    from .idw import idw_interpolation_at_points
    
    # Load data
    wells = gpd.read_file(wells_path)
    tracts = gpd.read_file(tracts_path)
    
    print(f"[REGRESSION DEBUG] Loaded {len(wells)} wells and {len(tracts)} census tracts")
    
    # Get tract centroids
    tract_centroids = tracts.copy()
    tract_centroids['centroid'] = tract_centroids.geometry.centroid
    
    # Extract centroid coordinates
    centroid_points = []
    for idx, tract in tract_centroids.iterrows():
        centroid = tract['centroid']
        centroid_points.append((centroid.x, centroid.y))
    
    print(f"[REGRESSION DEBUG] Computing IDW interpolation at {len(centroid_points)} tract centroids...")
    
    # Perform IDW interpolation at tract centroids
    interpolated_values = idw_interpolation_at_points(wells_path, centroid_points, k=k)
    
    # Add interpolated values to tract data
    tract_centroids['nitrate_idw'] = interpolated_values
    tract_centroids['nitrate_mean'] = interpolated_values  # For compatibility with existing code
    tract_centroids['nitrate_median'] = interpolated_values
    tract_centroids['nitrate_std'] = 0  # No variation since it's interpolated
    tract_centroids['nitrate_min'] = interpolated_values
    tract_centroids['nitrate_max'] = interpolated_values
    tract_centroids['well_count'] = 1  # Mark as having data
    
    # Remove the centroid column and keep original geometry
    result = tract_centroids.drop(columns=['centroid'])
    
    print(f"[REGRESSION DEBUG] IDW interpolation completed for {len(result)} census tracts")
    
    return result

def analyze_hexbin_regression(regression_data):
    """
    Perform linear regression analysis on hexbin data.
    Mimics the reference project's regression approach.
    
    Args:
        regression_data (dict): Dictionary containing nitrate and cancer values from hexbins
    
    Returns:
        dict: Comprehensive regression analysis results
    """
    print("[HEXBIN REGRESSION DEBUG] Starting hexbin regression analysis...")
    
    nitrate_values = regression_data.get('nitrate_values', [])
    cancer_values = regression_data.get('cancer_values', [])
    
    if len(nitrate_values) == 0 or len(cancer_values) == 0:
        print("[HEXBIN REGRESSION DEBUG] No valid data for regression")
        return {
            'error': 'No valid data points for regression analysis',
            'valid_points': 0
        }
    
    if len(nitrate_values) != len(cancer_values):
        print(f"[HEXBIN REGRESSION DEBUG] Mismatched data lengths: {len(nitrate_values)} vs {len(cancer_values)}")
        return {
            'error': 'Mismatched data lengths between nitrate and cancer values',
            'valid_points': 0
        }
    
    # Convert to numpy arrays
    X = np.array(nitrate_values).reshape(-1, 1)  # Nitrate (independent variable)
    y = np.array(cancer_values)                  # Cancer rate (dependent variable)
    
    print(f"[HEXBIN REGRESSION DEBUG] Regression data: {len(X)} hexbins")
    print(f"[HEXBIN REGRESSION DEBUG] Nitrate range: {np.min(X):.3f} - {np.max(X):.3f}")
    print(f"[HEXBIN REGRESSION DEBUG] Cancer rate range: {np.min(y):.6f} - {np.max(y):.6f}")
    
    try:
        # Perform linear regression using scikit-learn
        model = LinearRegression()
        model.fit(X, y)
        
        # Get predictions
        y_pred = model.predict(X)
        
        # Calculate statistics
        slope = float(model.coef_[0])
        intercept = float(model.intercept_)
        r_squared = r2_score(y, y_pred)
        
        # Calculate residuals
        residuals = y - y_pred
        
        # Additional statistics using scipy
        # Pearson correlation coefficient
        correlation, _ = stats.pearsonr(nitrate_values, cancer_values)
        
        # Calculate standard errors (simplified approach)
        n = len(X)
        mse = np.mean(residuals ** 2)
        
        # Standard error of slope
        x_mean = np.mean(X)
        ss_x = np.sum((X - x_mean) ** 2)
        se_slope = np.sqrt(mse / ss_x) if ss_x > 0 else 0
        
        # Standard error of intercept
        se_intercept = np.sqrt(mse * (1/n + x_mean**2/ss_x)) if ss_x > 0 else 0
        
        # T-statistics
        t_slope = slope / se_slope if se_slope > 0 else 0
        t_intercept = intercept / se_intercept if se_intercept > 0 else 0
        
        # Degrees of freedom
        df = n - 2
        
        # P-values (two-tailed)
        p_slope = 2 * (1 - stats.t.cdf(abs(t_slope), df)) if df > 0 else 1.0
        p_intercept = 2 * (1 - stats.t.cdf(abs(t_intercept), df)) if df > 0 else 1.0
        
        # Format regression equation
        sign = '+' if intercept >= 0 else '-'
        equation = f"y = {slope:.6f}x {sign} {abs(intercept):.6f}"
        
        # Prepare results similar to the reference project
        results = {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_squared),
            'correlation': float(correlation),
            'equation': equation,
            'residuals': residuals.tolist(),
            'predicted_values': y_pred.tolist(),
            'observed_values': y.tolist(),
            'nitrate_values': nitrate_values,
            'cancer_values': cancer_values,
            'valid_points': int(n),
            'statistics': {
                'mse': float(mse),
                'rmse': float(np.sqrt(mse)),
                'se_slope': float(se_slope),
                'se_intercept': float(se_intercept),
                't_slope': float(t_slope),
                't_intercept': float(t_intercept),
                'p_slope': float(p_slope),
                'p_intercept': float(p_intercept),
                'degrees_freedom': int(df)
            },
            'regression_type': 'hexbin'
        }
        
        print(f"[HEXBIN REGRESSION DEBUG] Regression completed successfully:")
        print(f"  - Equation: {equation}")
        print(f"  - R²: {r_squared:.6f}")
        print(f"  - Correlation: {correlation:.6f}")
        print(f"  - Valid points: {n}")
        
        return results
        
    except Exception as e:
        print(f"[HEXBIN REGRESSION DEBUG] Error in regression analysis: {str(e)}")
        return {
            'error': f'Regression analysis failed: {str(e)}',
            'valid_points': len(X) if 'X' in locals() else 0
        }

if __name__ == "__main__":
    # Test the analysis
    print("Running regression analysis test...")
    results = run_comprehensive_analysis()
    if 'error' not in results:
        print(f"Analysis successful: {results['equation']}")
        print(f"R² = {results['r_squared']:.4f}")
    else:
        print(f"Analysis failed: {results['error']}")