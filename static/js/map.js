let idwLayer = null;

console.log("✅ map.js loaded and running!");

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

// IDW interpolation handler
function updateIDW() {
  console.log("🟢 updateIDW() triggered");

  const k = document.getElementById("kVal").value;
  const res = document.getElementById("resSlider").value;

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
    })
    .catch(err => {
      console.error("🔥 Fetch error:", err);
      alert("Failed to load IDW data.");
    });
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
  document.getElementById('kVal').value = '';
  document.getElementById('resSlider').value = '';
  document.getElementById('regressionEq').textContent = 'N/A';
  document.getElementById('r2Val').textContent = 'N/A';
}
