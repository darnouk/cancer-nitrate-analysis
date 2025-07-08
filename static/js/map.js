let idwLayer = null;
let progressInterval = null;
let startTime = null;
let isCalculationCancelled = false;

console.log("✅ map.js loaded and running! [Version: 2025-01-07-003 with direct slope/intercept]");

// Progress Bar Functions
function showProgressBar() {
  document.getElementById('progressOverlay').style.display = 'flex';
  startTime = Date.now();
  isCalculationCancelled = false;
  updateProgress(0, 'Initializing calculation...', 'Estimating time...');
}

function hideProgressBar() {
  document.getElementById('progressOverlay').style.display = 'none';
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

function updateProgress(percent, step, timeEst) {
  document.getElementById('progressBar').style.width = percent + '%';
  document.getElementById('progressPercent').textContent = Math.round(percent) + '%';
  document.getElementById('currentStep').textContent = step;
  document.getElementById('timeRemaining').textContent = timeEst;
}

function estimateTimeRemaining(percent, k, res) {
  if (percent <= 0) return 'Estimating time...';
  
  const elapsed = (Date.now() - startTime) / 1000; // seconds
  const totalEstimated = elapsed / (percent / 100);
  const remaining = totalEstimated - elapsed;
  
  if (remaining <= 0) return 'Almost done...';
  
  if (remaining < 60) {
    return `~${Math.round(remaining)} seconds remaining`;
  } else {
    const minutes = Math.floor(remaining / 60);
    const seconds = Math.round(remaining % 60);
    return `~${minutes}m ${seconds}s remaining`;
  }
}

function simulateProgress(k, res) {
  let progress = 0;
  const baseTime = 30; // Base time in seconds for k=2, res=10
  
  // Estimate total time based on parameters
  // Higher k = slightly more computation, lower res = much more computation
  const kFactor = k / 2; // k=2 is baseline
  const resFactor = Math.pow(10 / res, 1.5); // res=10 is baseline, lower res = exponentially more time
  const estimatedTotalTime = baseTime * kFactor * resFactor;
  
  progressInterval = setInterval(() => {
    if (isCalculationCancelled) {
      clearInterval(progressInterval);
      return;
    }
    
    const elapsed = (Date.now() - startTime) / 1000;
    
    // Progress simulation: slower at start, faster in middle, slower at end
    if (progress < 20) {
      progress += 0.5; // Slow start
      updateProgress(progress, 'Loading data and initializing...', estimateTimeRemaining(progress, k, res));
    } else if (progress < 40) {
      progress += 1;
      updateProgress(progress, 'Performing IDW interpolation...', estimateTimeRemaining(progress, k, res));
    } else if (progress < 80) {
      progress += 1.5; // Faster middle section
      updateProgress(progress, 'Computing tract centroids...', estimateTimeRemaining(progress, k, res));
    } else if (progress < 95) {
      progress += 0.8;
      updateProgress(progress, 'Running regression analysis...', estimateTimeRemaining(progress, k, res));
    } else if (progress < 98) {
      progress += 0.2; // Very slow at end
      updateProgress(progress, 'Finalizing results...', estimateTimeRemaining(progress, k, res));
    }
    
    // Don't let simulated progress exceed 98% until real completion
    if (progress > 98) progress = 98;
    
  }, 200); // Update every 200ms
}

function cancelCalculation() {
  isCalculationCancelled = true;
  hideProgressBar();
  // Reset regression results to initial state
  document.getElementById('regressionEq').textContent = 'Enter parameters and click Submit';
  document.getElementById('r2Val').textContent = 'Enter parameters and click Submit';
  document.getElementById('correlationVal').textContent = 'Enter parameters and click Submit';
  document.getElementById('countiesCount').textContent = 'Enter parameters and click Submit';
  
  console.log("🛑 Calculation cancelled by user");
}

// Initialize the map
const map = L.map('map').setView([44, -89.5], 7);

// Add base tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Load census tracts first
fetch('/static/data/cancer_tracts.geojson')
  .then(res => res.json())
  .then(tracts => {
    L.geoJSON(tracts, {
      style: feature => ({
        color: '#999',
        weight: 1,
        fillOpacity: 0.7,
        fillColor: getCancerColor(feature.properties.canrate * 100)
      }),
      onEachFeature: (feature, layer) => {
        const val = feature.properties.canrate;
        const percent = Math.round(val * 100);
        layer.bindPopup(`<b>Cancer Rate:</b> ${percent}%`);
      }
    }).addTo(map);

    // Load well data
    fetch('/static/data/well_nitrate.geojson')
      .then(res => res.json())
      .then(wells => {
        L.geoJSON(wells, {
          pointToLayer: (feature, latlng) => {
            const val = feature.properties.nitr_ran;
            const color = getNitrateColor(val);
            const rounded = Math.round(val * 100) / 100;
            return L.circleMarker(latlng, {
              radius: 3,
              fillColor: color,
              color: '#333',
              weight: 0.5,
              fillOpacity: 0.8
            }).bindPopup(`<b>Nitrate Concentration:</b> ${rounded} ppm`);
          }
        }).addTo(map);
      });
  });

// Do NOT perform regression analysis on page load - wait for user input!
// Initialize with waiting message
document.getElementById('regressionEq').textContent = 'Enter parameters and click Submit';
document.getElementById('r2Val').textContent = 'Enter parameters and click Submit';
document.getElementById('correlationVal').textContent = 'Enter parameters and click Submit';
document.getElementById('countiesCount').textContent = 'Enter parameters and click Submit';

// IDW interpolation handler
function updateIDW() {
  console.log("🟢 updateIDW() triggered");

  const k = document.getElementById("kVal").value;
  const res = document.getElementById("resSlider").value;

  // Validate inputs
  if (!k || !res) {
    alert("Please enter both Distance Decay Coefficient and Hexbin Areas values.");
    return;
  }

  // Show progress bar and start simulation
  showProgressBar();
  simulateProgress(parseFloat(k), parseInt(res));

  // Show loading message in sidebar
  document.getElementById('regressionEq').textContent = 'Computing...';
  document.getElementById('r2Val').textContent = 'Computing...';
  document.getElementById('correlationVal').textContent = 'Computing...';
  document.getElementById('countiesCount').textContent = 'Computing...';

  fetch(`/interpolate?k=${k}&res=${res}`)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (idwLayer) map.removeLayer(idwLayer);
      idwLayer = L.layerGroup();

      data.forEach(pt => {
        if (pt.x == null || pt.y == null || pt.nitrate == null) return;

        const circle = L.circleMarker([pt.y, pt.x], {
          radius: 2,
          fillColor: getNitrateColor(pt.nitrate),
          fillOpacity: 0.6,
          color: "#333",
          weight: 0.3
        }).bindPopup(`Nitrate: ${pt.nitrate.toFixed(2)} ppm`);

        idwLayer.addLayer(circle);
      });

      idwLayer.addTo(map);
      
      // Update regression analysis after interpolation using the same parameters
      console.log(`🟢 Running regression analysis with k=${k}, res=${res}`);
      performRegressionAnalysis(k, res);
    })
    .catch(err => {
      console.error("🔥 Fetch error:", err);
      hideProgressBar();
      alert("Failed to load IDW data.");
      
      // Reset to initial state
      document.getElementById('regressionEq').textContent = 'Enter parameters and click Submit';
      document.getElementById('r2Val').textContent = 'Enter parameters and click Submit';
      document.getElementById('correlationVal').textContent = 'Enter parameters and click Submit';
      document.getElementById('countiesCount').textContent = 'Enter parameters and click Submit';
    });
}

// Regression analysis function
function performRegressionAnalysis(k = null, res = null) {
  console.log(`🟢 Performing regression analysis with k=${k}, res=${res}...`);
  
  // Build URL with parameters if provided
  let url = '/regression';
  if (k !== null && res !== null) {
    url += `?k=${k}&res=${res}`;
  }
  
  fetch(url)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (data.error) {
        console.error("❌ Regression error:", data.error);
        document.getElementById('regressionEq').textContent = 'Error';
        document.getElementById('r2Val').textContent = 'Error';
        document.getElementById('correlationVal').textContent = 'Error';
        document.getElementById('countiesCount').textContent = 'Error';
        hideProgressBar();
        return;
      }
      
      // Complete the progress bar
      updateProgress(100, 'Complete!', 'Done');
      setTimeout(() => {
        hideProgressBar();
      }, 1000); // Show completion for 1 second
      
      // Update UI with regression results
      document.getElementById('regressionEq').textContent = data.equation || 'N/A';
      document.getElementById('r2Val').textContent = data.r_squared ? data.r_squared.toFixed(4) : 'N/A';
      document.getElementById('correlationVal').textContent = data.correlation ? data.correlation.toFixed(4) : 'N/A';
      document.getElementById('countiesCount').textContent = data.n_tracts || 'N/A';
      
      console.log("✅ Regression analysis completed:", {
        equation: data.equation,
        r_squared: data.r_squared,
        correlation: data.correlation,
        is_significant: data.is_significant,
        n_counties: data.n_counties
      });
      
      // Log interpretation for debugging
      if (data.interpretation) {
        console.log("📊 Interpretation:", data.interpretation);
      }
    })
    .catch(err => {
      console.error("🔥 Regression fetch error:", err);
      hideProgressBar();
      document.getElementById('regressionEq').textContent = 'Failed to load';
      document.getElementById('r2Val').textContent = 'Failed to load';
      document.getElementById('correlationVal').textContent = 'Failed to load';
      document.getElementById('countiesCount').textContent = 'Failed to load';
    });
}

// Toggle analysis input fields based on selected type
function toggleAnalysisInputs() {
  const analysisType = document.getElementById('analysisType').value;
  const hexbinInputs = document.getElementById('hexbinInputs');
  const gridInputs = document.getElementById('gridInputs');
  
  if (analysisType === 'hexbin') {
    hexbinInputs.style.display = 'block';
    gridInputs.style.display = 'none';
  } else {
    hexbinInputs.style.display = 'none';
    gridInputs.style.display = 'block';
  }
}

// Updated main analysis function that handles both types
function updateAnalysis() {
  console.log("🟢 updateAnalysis() triggered");
  
  const analysisType = document.getElementById('analysisType').value;
  
  if (analysisType === 'hexbin') {
    updateHexbinAnalysis();
  } else {
    updateIDW();
  }
}

// New function for hexbin analysis
function updateHexbinAnalysis() {
  console.log("🟢 updateHexbinAnalysis() triggered");

  const k = document.getElementById("kVal").value;
  const hexbinArea = document.getElementById("hexbinArea").value;

  // Validate inputs
  if (!k || !hexbinArea) {
    alert("Please enter both Distance Decay Coefficient and Hexbin Area values.");
    return;
  }

  // Validate ranges (similar to reference project)
  const kNum = parseFloat(k);
  const hexbinNum = parseFloat(hexbinArea);
  
  if (hexbinNum < 0.01 || hexbinNum > 10) {
    alert("Enter a hexbin area between 0.01 and 10 square miles");
    return;
  }
  
  if (kNum < 0 || kNum > 100) {
    alert("Enter a distance decay coefficient between 0 and 100");
    return;
  }

  // Show progress bar and start simulation
  showProgressBar();
  simulateHexbinProgress(kNum, hexbinNum);

  // Show loading message in sidebar
  document.getElementById('regressionEq').textContent = 'Computing hexbin analysis...';
  document.getElementById('r2Val').textContent = 'Computing hexbin analysis...';
  document.getElementById('correlationVal').textContent = 'Computing hexbin analysis...';
  document.getElementById('countiesCount').textContent = 'Computing hexbin analysis...';

  fetch(`/hexbin_analysis?hexbin_area=${hexbinArea}&k=${k}`)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
      return res.json();
    })
    .then(data => {
      console.log("🟢 Hexbin analysis response received:", data);
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Clear existing layers
      if (idwLayer) map.removeLayer(idwLayer);
      idwLayer = L.layerGroup();

      // Display hexbins on map
      if (data.interpolation && data.interpolation.hexbins_geojson) {
        // FIRST: Update regression display to get slope/intercept
        if (data.regression && !data.regression.error) {
          updateRegressionDisplay(data.regression);
        }
        
        // THEN: Display hexbins with proper coloring
        displayHexbins(data.interpolation.hexbins_geojson);
      }
      
      // Complete the progress bar
      if (data.regression && !data.regression.error) {
        updateProgress(100, 'Analysis complete!', 'Complete');
        setTimeout(hideProgressBar, 1000);
      } else {
        throw new Error(data.regression?.error || 'Regression analysis failed');
      }
    })
    .catch(err => {
      console.error("🔥 Hexbin analysis error:", err);
      hideProgressBar();
      alert(`Hexbin analysis failed: ${err.message}`);
      
      // Reset to initial state
      document.getElementById('regressionEq').textContent = 'Enter parameters and click Submit';
      document.getElementById('r2Val').textContent = 'Enter parameters and click Submit';
      document.getElementById('correlationVal').textContent = 'Enter parameters and click Submit';
      document.getElementById('countiesCount').textContent = 'Enter parameters and click Submit';
    });
}

// Progress simulation for hexbin analysis
function simulateHexbinProgress(k, hexbinArea) {
  let progress = 0;
  const baseTime = 25; // Base time for hexbin analysis
  
  // Estimate total time based on parameters
  const kFactor = k / 2;
  const areeFactor = 15 / hexbinArea; // Smaller hexbins = more computation
  const estimatedTotalTime = baseTime * kFactor * areeFactor;
  
  progressInterval = setInterval(() => {
    if (isCalculationCancelled) {
      clearInterval(progressInterval);
      return;
    }
    
    const elapsed = (Date.now() - startTime) / 1000;
    
    if (progress < 15) {
      progress += 1;
      updateProgress(progress, 'Generating hexagonal grid...', estimateTimeRemaining(progress, k, hexbinArea));
    } else if (progress < 35) {
      progress += 1.5;
      updateProgress(progress, 'Interpolating nitrate to hexbins...', estimateTimeRemaining(progress, k, hexbinArea));
    } else if (progress < 65) {
      progress += 1.8;
      updateProgress(progress, 'Aggregating cancer data to hexbins...', estimateTimeRemaining(progress, k, hexbinArea));
    } else if (progress < 90) {
      progress += 1.2;
      updateProgress(progress, 'Performing hexbin regression...', estimateTimeRemaining(progress, k, hexbinArea));
    } else if (progress < 98) {
      progress += 0.3;
      updateProgress(progress, 'Finalizing hexbin visualization...', estimateTimeRemaining(progress, k, hexbinArea));
    }
    
    if (progress > 98) progress = 98;
    
  }, 300);
}

// Global variables to store current regression equation and residuals data
let currentRegressionSlope = null;
let currentRegressionIntercept = null;
let regressionResiduals = null;
let residualStandardDeviation = null;

// Display Hexbins on the map
function displayHexbins(geojsonData) {
  try {
    console.log(`🎨 Displaying ${geojsonData.features.length} hexbin features`);
    
    // Calculate residuals if regression data is available
    regressionResiduals = calculateResiduals(geojsonData);
    
    const canUseResidualColoring = regressionResiduals && currentRegressionSlope && currentRegressionIntercept;
    console.log(`🎨 Using residual coloring: ${canUseResidualColoring}`);
    
    // Create hexbin layer
    const hexbinLayer = L.geoJSON(geojsonData, {
      style: function(feature) {
        // Use regression residuals for coloring if available
        if (canUseResidualColoring) {
          const props = feature.properties;
          const nitrate = props.nitr_ran_interpolated;
          const observedRate = props.canrate_aggregated;
          
          if (nitrate !== undefined && observedRate !== undefined && 
              !isNaN(nitrate) && !isNaN(observedRate)) {
            const predictedRate = currentRegressionSlope * nitrate + currentRegressionIntercept;
            const residual = observedRate - predictedRate;
            const standardizedResidual = residual / regressionResiduals.standardDeviation;
            
            return {
              fillColor: getResidualColor(standardizedResidual),
              weight: 0.5,
              opacity: 1,
              color: '#222',
              fillOpacity: 0.8
            };
          } else {
            // Gray color for hexbins without valid data
            return {
              fillColor: '#999999',
              weight: 0.5,
              opacity: 1,
              color: '#222',
              fillOpacity: 0.5
            };
          }
        }
        
        // Fallback to nitrate-based coloring if no regression data
        const nitrateValue = feature.properties.nitr_ran_interpolated || 0;
        console.log(`🎨 Fallback to nitrate coloring: ${nitrateValue.toFixed(3)}`);
        return {
          fillColor: getNitrateColor(nitrateValue),
          weight: 0.5,
          opacity: 1,
          color: '#222',
          fillOpacity: 0.7
        };
      },
      onEachFeature: function(feature, layer) {
        // Create popup with requested format
        let popupContent = '';
        
        // Nitrate value
        if (feature.properties.nitr_ran_interpolated !== undefined) {
          popupContent += `<strong>Nitrate:</strong> ${feature.properties.nitr_ran_interpolated.toFixed(1)} ppm<br>`;
        }
        
        // Observed Cancer Rate
        if (feature.properties.canrate_aggregated !== undefined) {
          popupContent += `<strong>Observed Cancer Rate:</strong> ${(feature.properties.canrate_aggregated * 100).toFixed(1)}% of census tract population<br>`;
        }
        
        // Predicted Cancer Rate (calculate from regression equation)
        if (feature.properties.nitr_ran_interpolated !== undefined && 
            currentRegressionSlope !== null && currentRegressionIntercept !== null) {
          const nitrateVal = feature.properties.nitr_ran_interpolated;
          const predictedRate = (currentRegressionSlope * nitrateVal + currentRegressionIntercept) * 100;
          popupContent += `<strong>Predicted Cancer Rate:</strong> ${predictedRate.toFixed(1)}% of census tract population<br>`;
          
          // Add residual information
          const observedRate = feature.properties.canrate_aggregated;
          if (observedRate !== undefined && regressionResiduals) {
            const residual = observedRate - (predictedRate / 100);
            const standardizedResidual = residual / regressionResiduals.standardDeviation;
            popupContent += `<strong>Residual:</strong> ${standardizedResidual.toFixed(2)} standard deviations`;
          }
        }
        
        if (popupContent) {
          layer.bindPopup(popupContent);
        }
      }
    });
    
    idwLayer.addLayer(hexbinLayer);
    idwLayer.addTo(map);
    
    // ALWAYS display residuals legend for hexbin analysis, regardless of data quality
    addRegressionResidualsLegend();
    console.log("🟢 Always showing residuals legend for hexbin analysis");
    
    console.log("🟢 Hexbins displayed on map");
    
  } catch (error) {
    console.error("🔥 Error displaying hexbins:", error);
  }
}

// Update regression display with new data structure
function updateRegressionDisplay(regressionData) {
  try {
    console.log("🔍 Updating regression display with:", regressionData);
    
    document.getElementById('regressionEq').textContent = regressionData.equation || 'N/A';
    document.getElementById('r2Val').textContent = (regressionData.r_squared || 0).toFixed(6);
    document.getElementById('correlationVal').textContent = (regressionData.correlation || 0).toFixed(6);
    document.getElementById('countiesCount').textContent = regressionData.valid_points || 0;
    
    // Extract slope and intercept - use direct values if available, otherwise parse equation
    if (regressionData.slope !== undefined && regressionData.intercept !== undefined) {
      // Use direct slope and intercept from backend
      currentRegressionSlope = regressionData.slope;
      currentRegressionIntercept = regressionData.intercept;
      console.log(`✅ Using direct regression parameters: slope=${currentRegressionSlope}, intercept=${currentRegressionIntercept}`);
    } else if (regressionData.equation && regressionData.equation !== 'N/A') {
      // Fallback to parsing equation
      console.log(`🔍 Parsing equation: "${regressionData.equation}"`);
      
      const match = regressionData.equation.match(/y\s*=\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)x\s*([-+])\s*([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)/);
      if (match) {
        currentRegressionSlope = parseFloat(match[1]);
        currentRegressionIntercept = parseFloat(match[2] + match[3]);
        console.log(`✅ Parsed regression parameters: slope=${currentRegressionSlope}, intercept=${currentRegressionIntercept}`);
      } else {
        console.log("⚠️ Could not parse regression equation:", regressionData.equation);
        currentRegressionSlope = null;
        currentRegressionIntercept = null;
      }
    } else {
      console.log("⚠️ No regression data available");
      currentRegressionSlope = null;
      currentRegressionIntercept = null;
    }
    
    console.log("🟢 Regression display updated");
  } catch (error) {
    console.error("🔥 Error updating regression display:", error);
  }
}

// Color scales
function getNitrateColor(val) {
  return val > 11.66 ? '#983404' :
         val > 6.72  ? '#d85e0d' :
         val > 3.84  ? '#fe9928' :
         val > 1.44  ? '#feda8e' :
                       '#ffffcf';
}

function getCancerColor(val) {
  return val > 58 ? '#421f6f' :
         val > 33 ? '#69609c' :
         val > 17 ? '#9c96bf' :
         val > 6  ? '#cec9e3' :
                    '#f0eff4';
}

// Color scheme for regression residuals (Standard Deviation of Regression)
function getResidualColor(standardizedResidual) {
  console.log(`🎨 Getting residual color for: ${standardizedResidual.toFixed(3)}`);
  
  if (standardizedResidual < -2) {
    return '#006837'; // Dark green (Underpredicting)
  } else if (standardizedResidual >= -2 && standardizedResidual < -1) {
    return '#31a354'; // Light green
  } else if (standardizedResidual >= -1 && standardizedResidual <= 1) {
    return '#ffff00'; // Yellow
  } else if (standardizedResidual > 1 && standardizedResidual <= 2) {
    return '#fd8d3c'; // Orange
  } else {
    return '#bd0026'; // Red (Overpredicting)
  }
}

// Calculate residuals and their standard deviation
function calculateResiduals(geojsonData) {
  if (!currentRegressionSlope || !currentRegressionIntercept) {
    console.log("⚠️ Cannot calculate residuals: no regression equation available");
    console.log(`  Slope: ${currentRegressionSlope}, Intercept: ${currentRegressionIntercept}`);
    return null;
  }
  
  const residuals = [];
  const validFeatures = [];
  
  geojsonData.features.forEach((feature, index) => {
    const props = feature.properties;
    const nitrate = props.nitr_ran_interpolated;
    const observedRate = props.canrate_aggregated;
    
    if (nitrate !== undefined && observedRate !== undefined && 
        !isNaN(nitrate) && !isNaN(observedRate)) {
      const predictedRate = currentRegressionSlope * nitrate + currentRegressionIntercept;
      const residual = observedRate - predictedRate;
      
      residuals.push(residual);
      validFeatures.push({
        feature: feature,
        residual: residual,
        predicted: predictedRate
      });
      
      if (index < 3) { // Debug first few features
        console.log(`  Feature ${index}: nitrate=${nitrate.toFixed(3)}, observed=${observedRate.toFixed(3)}, predicted=${predictedRate.toFixed(3)}, residual=${residual.toFixed(3)}`);
      }
    } else {
      if (index < 3) {
        console.log(`  Feature ${index}: INVALID - nitrate=${nitrate}, observed=${observedRate}`);
      }
    }
  });
  
  console.log(`🔍 Residuals calculation: ${validFeatures.length} valid features out of ${geojsonData.features.length} total`);
  
  if (residuals.length < 3) {
    console.log("❌ Not enough valid data for residual calculation");
    return null;
  }
  
  // Calculate standard deviation of residuals
  const mean = residuals.reduce((sum, r) => sum + r, 0) / residuals.length;
  const variance = residuals.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / residuals.length;
  const stdDev = Math.sqrt(variance);
  
  console.log(`🟢 Calculated residuals: mean=${mean.toFixed(6)}, stdDev=${stdDev.toFixed(6)}, count=${residuals.length}`);
  
  return {
    residuals: residuals,
    standardDeviation: stdDev,
    validFeatures: validFeatures
  };
}

// Legends
const nitrateLegend = L.control({ position: 'bottomright' });
nitrateLegend.onAdd = function () {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<h4>Nitrate Concentration (ppm)</h4>';
  div.innerHTML += '<div><span style="background:#ffffcf"></span>-1.89 – 1.44 ppm</div>';
  div.innerHTML += '<div><span style="background:#feda8e"></span>1.45 – 3.84 ppm</div>';
  div.innerHTML += '<div><span style="background:#fe9928"></span>3.85 – 6.71 ppm</div>';
  div.innerHTML += '<div><span style="background:#d85e0d"></span>6.73 – 11.52 ppm</div>';
  div.innerHTML += '<div><span style="background:#983404"></span>11.67 – 17.07 ppm</div>';
  return div;
};
nitrateLegend.addTo(map);

const cancerLegend = L.control({ position: 'bottomright' });
cancerLegend.onAdd = function () {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<h4>Cancer Rate (%)</h4>';
  div.innerHTML += '<div><span style="background:#f0eff4"></span>0–6%</div>';
  div.innerHTML += '<div><span style="background:#cec9e3"></span>7–17%</div>';
  div.innerHTML += '<div><span style="background:#9c96bf"></span>18–33%</div>';
  div.innerHTML += '<div><span style="background:#69609c"></span>34–58%</div>';
  div.innerHTML += '<div><span style="background:#421f6f"></span>59–100%</div>';
  return div;
};
cancerLegend.addTo(map);

// Sidebar + reset
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.style.display = sidebar.style.display === 'flex' ? 'none' : 'flex';
}
document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);

function resetInputs() {
  // Remove regression residuals legend FIRST
  removeRegressionResidualsLegend();
  
  // Reset analysis type to default
  document.getElementById('analysisType').value = 'hexbin';
  toggleAnalysisInputs();
  
  // Reset input values to defaults
  document.getElementById('kVal').value = '2';
  document.getElementById('hexbinArea').value = '0.1';
  document.getElementById('resSlider').value = '5';
  
  // Reset results display
  document.getElementById('regressionEq').textContent = 'Enter parameters and click Submit';
  document.getElementById('r2Val').textContent = 'Enter parameters and click Submit';
  document.getElementById('correlationVal').textContent = 'Enter parameters and click Submit';
  document.getElementById('countiesCount').textContent = 'Enter parameters and click Submit';
  
  // Remove any existing layers
  if (idwLayer) {
    map.removeLayer(idwLayer);
    idwLayer = null;
  }
  
  // Clear regression data
  currentRegressionSlope = null;
  currentRegressionIntercept = null;
  regressionResiduals = null;
  residualStandardDeviation = null;
  
  console.log("🟢 Reset complete - all layers and legends cleared");
}

// Regression Residuals Legend
let regressionResidualsLegend = null;

function addRegressionResidualsLegend() {
  // Remove existing legend if present
  removeRegressionResidualsLegend();
  
  regressionResidualsLegend = L.control({ position: 'bottomright' });
  regressionResidualsLegend.onAdd = function () {
    const div = L.DomUtil.create('div', 'legend');
    div.style.marginBottom = '10px'; // Add space above cancer legend
    div.innerHTML = '<h4>Standard Deviation of<br>Regression</h4>';
    div.innerHTML += '<div><span style="background:#006837"></span>&lt;-2 Std. Dev. (Underprediction)</div>';
    div.innerHTML += '<div><span style="background:#31a354"></span>-2 Std. Dev. — -1 Std. Dev.</div>';
    div.innerHTML += '<div><span style="background:#ffff00"></span>-1 Std. Dev. — 1 Std. Dev.</div>';
    div.innerHTML += '<div><span style="background:#fd8d3c"></span>1 Std. Dev. — 2 Std. Dev.</div>';
    div.innerHTML += '<div><span style="background:#bd0026"></span>&gt;2 Std. Dev. (Overprediction)</div>';
    return div;
  };
  regressionResidualsLegend.addTo(map);
  
  console.log("🟢 Added regression residuals legend");
}

function removeRegressionResidualsLegend() {
  if (regressionResidualsLegend) {
    try {
      map.removeControl(regressionResidualsLegend);
      regressionResidualsLegend = null;
      console.log("🟢 Removed regression residuals legend");
    } catch (e) {
      console.log("⚠️ Error removing legend, forcing cleanup:", e);
      regressionResidualsLegend = null;
    }
  }
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Set default analysis type and toggle inputs
  toggleAnalysisInputs();
  console.log("🟢 Page initialized with hexbin analysis as default");
});
