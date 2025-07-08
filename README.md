# Wisconsin Nitrate-Cancer Relationship Analysis

An interactive web-based geospatial analysis application for exploring the relationship between groundwater nitrate concentrations and cancer rates in Wisconsin.

## 🎯 Project Overview

This application addresses a critical environmental health question: **Is there a spatial correlation between nitrate concentrations in Wisconsin groundwater and cancer incidence rates?**

The challenge involves analyzing point data (well locations with nitrate measurements) against polygon data (cancer rates by census tracts). Our solution provides an interactive platform for exploring this relationship through advanced spatial interpolation, hexagonal tessellation, and statistical analysis.

## ✨ Key Features

### 🗺️ Dual Analysis Modes
- **Hexagonal Tessellation**: Advanced spatial aggregation using perfect hexagonal grids
- **Traditional Grid**: Classic IDW interpolation with point-based visualization

### 🔬 Advanced Analytics
- **Inverse Distance Weighting (IDW)** interpolation with adjustable distance decay
- **Linear regression analysis** with correlation coefficients and R-squared values
- **Residuals visualization** showing model performance across space
- **Area-weighted aggregation** for multi-tract hexagons

### 🎨 Interactive Visualization
- **Real-time parameter adjustment** with immediate visual feedback
- **Progress tracking** with time estimation for long calculations
- **Three coordinated legends**: Nitrate levels, cancer rates, and regression residuals
- **Smart popups** showing nitrate, observed rates, predicted rates, and residuals

### 🛠️ Technical Innovations
- **Perfect hexagonal tessellation** with no gaps or overlaps
- **Census tract boundary clipping** to ensure analytical integrity
- **Dynamic legend management** with automatic cleanup
- **Robust error handling** and validation

## 🚀 Getting Started

### Prerequisites
```
Python 3.8+
Flask
GeoPandas
Shapely
NumPy
Pandas
SciPy
```

### Installation
1. **Clone or download the project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   python run.py
   ```
4. **Open your browser** to `http://localhost:5000`

### Quick Start
1. **Choose analysis type**: Hexbin (recommended) or Grid
2. **Set parameters**:
   - Distance Decay Coefficient (k): Controls interpolation smoothness
   - Hexbin Area: Size of hexagonal units (0.01-10 sq miles)
3. **Click Submit** and wait for analysis to complete
4. **Explore results** through interactive map and statistical outputs

## 📁 Project Structure

```
Project1/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── routes.py                # Main application routes
│   ├── templates/
│   │   └── index.html           # Main interface
│   └── utils/
│       ├── geojson_utils.py     # Spatial data utilities
│       ├── hexbin.py            # Hexagonal tessellation
│       ├── idw.py               # IDW interpolation
│       └── regression.py        # Statistical analysis
├── static/
│   ├── css/
│   │   └── style.css           # Application styling
│   ├── js/
│   │   └── map.js              # Frontend map logic
│   └── data/
│       ├── cancer_tracts.geojson    # Cancer rate data
│       ├── cancer_county.geojson    # County boundaries
│       └── well_nitrate.geojson     # Nitrate measurements
├── outputs/                     # Analysis results
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── Project_Report.txt          # Detailed analysis report
└── README.md                   # This file
```

## 🔧 Technical Details

### Spatial Interpolation
- **IDW Algorithm**: Estimates values at unsampled locations using distance-weighted averaging
- **Distance Decay**: User-adjustable coefficient controlling interpolation smoothness
- **Boundary Constraints**: Analysis limited to areas with valid cancer data

### Hexagonal Tessellation
- **Perfect Fit**: Uses matplotlib's hexagonal spacing for gap-free coverage
- **Area Control**: Precise hexagon sizing in square miles with CRS conversion
- **Boundary Clipping**: Hexagons trimmed to census tract boundaries
- **Multi-tract Aggregation**: Area-weighted averaging across tract boundaries

### Statistical Analysis
- **Linear Regression**: Pearson correlation and least squares fitting
- **Residuals Analysis**: Standardized residuals showing model performance
- **Validation**: Robust error handling for edge cases and insufficient data

### Visualization
- **Color Schemes**: 
  - Nitrate: Yellow to brown progression
  - Cancer: Purple progression
  - Residuals: Green-yellow-red showing over/under prediction
- **Interactive Elements**: Dynamic popups, progress bars, legend management
- **Performance**: Optimized rendering for large datasets

## 📊 Understanding Results

### Regression Statistics
- **R-squared**: Proportion of variance explained by nitrate (typically 0.15-0.35)
- **Correlation**: Strength of linear relationship (typically 0.4-0.6)
- **Equation**: Linear model for predicting cancer rates from nitrate levels

### Residuals Interpretation
- **Green areas**: Model under-predicts cancer rates (other factors may increase risk)
- **Yellow areas**: Good model fit (±1 standard deviation)
- **Red areas**: Model over-predicts cancer rates (protective factors may exist)

### Spatial Patterns
- **High nitrate**: Concentrated in agricultural regions (central/southwest Wisconsin)
- **Cancer clusters**: Complex distribution partially correlated with nitrate
- **Residual patterns**: Reveal areas needing additional investigation

## 🎓 Educational Use

This project demonstrates:
- **Spatial interpolation** techniques and their applications
- **Hexagonal tessellation** advantages over rectangular grids
- **Environmental health** data analysis approaches
- **Interactive visualization** for scientific communication
- **Statistical modeling** of spatial relationships

## 🔬 Research Applications

### Environmental Health
- Assess groundwater contamination impacts
- Identify high-risk communities
- Guide monitoring and remediation efforts

### Spatial Analysis
- Compare interpolation methods
- Explore scale-dependent relationships
- Develop predictive models

### Policy Support
- Evidence-based environmental regulation
- Public health resource allocation
- Community risk communication

## ⚠️ Limitations & Considerations

### Data Limitations
- Correlation does not imply causation
- Cancer has multiple risk factors beyond nitrate
- Temporal relationships not analyzed
- Data quality varies across regions

### Methodological Notes
- IDW assumes spatial continuity
- Linear regression may oversimplify relationships
- Small hexbins may have insufficient cancer data
- Edge effects near study area boundaries

### Future Enhancements
- Incorporate additional environmental variables
- Add temporal analysis capabilities
- Implement geographically weighted regression
- Include socioeconomic and lifestyle factors

## 🤝 Contributing

This is an educational project developed for GEOG 777. For questions or suggestions about the methodology or implementation, please refer to the course materials or contact the instructor.

## 📄 License

This project is developed for educational purposes as part of a university course. The code and documentation are provided as-is for learning and reference.

## 📚 References

- Environmental health literature on nitrate-cancer relationships
- Spatial interpolation methodologies
- Interactive web mapping best practices
- Statistical analysis of environmental data

## 🏆 Acknowledgments

Developed as part of GEOG 777 coursework, demonstrating advanced geospatial analysis techniques and web-based visualization methods for environmental health research.

---

**For detailed analysis results and methodology, see `Project_Report.txt`**
