// Global Variables
let mainChartInstance = null;
let fiftyTwoWeekChartInstance = null;
let currentTimeframe = 'YTD';
let autoRefreshInterval = null;
let masterData = null; 

// ============================================
//  MODAL LOGIC
// ============================================
function openModal(type, data) {
    document.getElementById('m-name').innerText = data.name;
    const tagElem = document.getElementById('m-tag');
    
    if (type === 'ipo') {
        tagElem.innerText = 'DRHP Filed';
        tagElem.className = 'modal-tag ipo';
        document.getElementById('lbl-1').innerText = 'Expected Date';
        document.getElementById('lbl-2').innerText = 'Price Band';
        document.getElementById('lbl-3').innerText = 'Issue Size';
        document.getElementById('lbl-4').innerText = 'Est. Valuation';
        document.getElementById('lbl-5').innerText = 'Sector';
        document.getElementById('lbl-6').innerText = 'Lead Manager';
        
        document.getElementById('val-1').innerText = data.date;
        document.getElementById('val-2').innerText = data.price;
        document.getElementById('val-3').innerText = data.size;
        document.getElementById('val-4').innerText = data.valuation;
        document.getElementById('val-5').innerText = data.sector;
        document.getElementById('val-6').innerText = 'Goldman Sachs';

    } else if (type === 'stock') {
        tagElem.innerText = 'Index Constituent';
        tagElem.className = 'modal-tag stock';
        document.getElementById('lbl-1').innerText = 'Market Cap';
        document.getElementById('lbl-2').innerText = 'Current Price';
        document.getElementById('lbl-3').innerText = '52W High';
        document.getElementById('lbl-4').innerText = '52W Low';
        document.getElementById('lbl-5').innerText = 'Sector';
        document.getElementById('lbl-6').innerText = 'Index Weight';
        
        document.getElementById('val-1').innerText = data.mktCap;
        document.getElementById('val-2').innerText = data.price;
        document.getElementById('val-3').innerText = data.high;
        document.getElementById('val-4').innerText = data.low;
        document.getElementById('val-5').innerText = data.sector;
        document.getElementById('val-6').innerText = data.weight;
    }
    
    document.getElementById('info-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('info-modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('info-modal');
    if (event.target == modal) modal.style.display = "none";
}

// ============================================
//  DUMMY DATA GENERATORS
// ============================================
function generateDummyIPOs() {
    const grid = document.getElementById('ipo-grid');
    const companies = [
        { name: "Zepto", sector: "Quick Commerce" }, { name: "Swiggy", sector: "Food Delivery" },
        { name: "PhonePe", sector: "Fintech" }, { name: "Ather Energy", sector: "EV Mfg" },
        { name: "Pine Labs", sector: "Fintech" }, { name: "Lenskart", sector: "E-commerce" },
        { name: "Dream11", sector: "Gaming" }, { name: "OfBusiness", sector: "B2B E-comm" },
        { name: "Ola Electric", sector: "EV Mfg" }, { name: "FirstCry", sector: "E-commerce" }
    ];
    
    let htmlContent = '';
    companies.forEach((company) => {
        const randomDays = Math.floor(Math.random() * 90) + 1;
        const ipoDate = new Date(); ipoDate.setDate(ipoDate.getDate() + randomDays);
        const dateStr = ipoDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const basePrice = Math.floor(Math.random() * 800) + 100;
        
        // Using Rs. to be safe
        const priceStr = `Rs. ${basePrice} - Rs. ${basePrice + 50}`;
        const issueSize = (Math.floor(Math.random() * 50) + 15) * 100;
        const valuation = issueSize * 5;

        // Safely stringifying the object for HTML injection
        const dataObj = {
            name: company.name,
            date: dateStr,
            price: priceStr,
            size: `Rs. ${issueSize.toLocaleString()} Cr`,
            valuation: `Rs. ${valuation.toLocaleString()} Cr`,
            sector: company.sector
        };
        // Replace double quotes to avoid breaking the HTML attribute
        const safeDataStr = JSON.stringify(dataObj).replace(/"/g, '&quot;');
        
        htmlContent += `
            <div class="ipo-card" onclick="openModal('ipo', ${safeDataStr})">
                <div class="ipo-name">${company.name}</div>
                <div class="ipo-date">Expected: ${dateStr}</div>
                <div class="ipo-price">${priceStr}</div>
            </div>
        `;
    });
    grid.innerHTML = htmlContent;
}

function generateDummyComposition() {
        const grid = document.getElementById('comp-grid');
        const stocks = [
            { ticker: "PAYTM", name: "One 97 Communications", sector: "Fintech" },
            { ticker: "ZOMATO", name: "Zomato Ltd", sector: "Food Tech" },
            { ticker: "NYKAA", name: "FSN E-Commerce", sector: "E-commerce" },
            { ticker: "POLICYBZR", name: "PB Fintech", sector: "Fintech" },
            { ticker: "DELHIVERY", name: "Delhivery Ltd", sector: "Logistics" },
            { ticker: "CARTRADE", name: "CarTrade Tech", sector: "Auto Tech" },
            { ticker: "EASEMYTRIP", name: "Easy Trip Planners", sector: "Travel Tech" },
            { ticker: "NAZARA", name: "Nazara Technologies", sector: "Gaming" }
        ];

        let htmlContent = '';
        stocks.forEach(stock => {
            const price = Math.floor(Math.random() * 2000) + 100;
            const mktCap = (Math.floor(Math.random() * 500) + 50) * 100;
            const weight = (Math.random() * 15).toFixed(1);
            
            const dataObj = {
                name: stock.name,
                mktCap: `Rs. ${mktCap.toLocaleString()} Cr`,
                price: `Rs. ${price}`,
                high: `Rs. ${price + 200}`,
                low: `Rs. ${price - 100}`,
                sector: stock.sector,
                weight: `${weight}%`
            };
            const safeDataStr = JSON.stringify(dataObj).replace(/"/g, '&quot;');

            htmlContent += `
            <div class="comp-card" onclick="openModal('stock', ${safeDataStr})">
                <div class="comp-ticker">${stock.ticker}</div>
                <div class="comp-name">${stock.name}</div>
                <div class="comp-stats">
                    <div><span class="c-stat-val">Rs. ${price}</span><br><span class="c-stat-lbl">Price</span></div>
                        <div><span class="c-stat-val" style="color:var(--accent-neon);">${weight}%</span><br><span class="c-stat-lbl">Weight</span></div>
                </div>
            </div>
            `;
        });
        grid.innerHTML = htmlContent;
}

// ============================================
//  MAIN CHART & DATA LOGIC
// ============================================
async function fetchMarketData() {
    try {
        console.log("Preparing to fetch data from Python API...");
        const end = new Date();
        let start = new Date();
        start.setFullYear(end.getFullYear() - 1);
        const startDateStr = start.toISOString().split('T')[0];

        const apiUrl = '/api/startups/chart?start=${startDateStr}';
        console.log("Pinging: ", apiUrl);

        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error("Network response was not ok");
        
        masterData = await response.json();
        console.log("Data successfully received!", masterData);

        let lastKnown = null;
        for (let i = 0; i < masterData.nifty_index.length; i++) {
            if (masterData.nifty_index[i] !== null) lastKnown = masterData.nifty_index[i];
            else if (lastKnown !== null) masterData.nifty_index[i] = lastKnown;
        }
        lastKnown = null;
        for (let i = masterData.nifty_index.length - 1; i >= 0; i--) {
            if (masterData.nifty_index[i] !== null) lastKnown = masterData.nifty_index[i];
            else if (lastKnown !== null) masterData.nifty_index[i] = lastKnown;
        }
        
        renderTimeframe(currentTimeframe);
        draw52WeekChart(masterData);

    } catch (error) {
        console.error("CRITICAL API ERROR:", error);
        document.getElementById('val-current').innerText = "ERROR";
        document.getElementById('val-current').style.color = "red";
    }
}

function renderTimeframe(tf) {
    if (!masterData || masterData.dates.length === 0) return;

    const end = new Date();
    let targetDate = new Date();
    if (tf === '1W') targetDate.setDate(end.getDate() - 7);
    if (tf === '1M') targetDate.setMonth(end.getMonth() - 1);
    if (tf === '3M') targetDate.setMonth(end.getMonth() - 3);
    if (tf === 'YTD') targetDate = new Date(end.getFullYear(), 0, 1);
    if (tf === '1Y') targetDate.setFullYear(end.getFullYear() - 1);
    
    const targetDateStr = targetDate.toISOString().split('T')[0];
    let startIndex = 0;
    for (let i = 0; i < masterData.dates.length; i++) {
        if (masterData.dates[i] >= targetDateStr) { startIndex = i; break; }
    }

    const slicedDates = masterData.dates.slice(startIndex);
    const rawSlicedStartup = masterData.startup_index.slice(startIndex);
    const rawSlicedNifty = masterData.nifty_index.slice(startIndex);

    const baseStartup = rawSlicedStartup[0];
    const slicedStartup = rawSlicedStartup.map(val => (val / baseStartup) * 100);
    const baseNifty = rawSlicedNifty[0];
    const slicedNifty = rawSlicedNifty.map(val => (val / baseNifty) * 100);

    const latest = slicedStartup[slicedStartup.length - 1];
    const firstInPeriod = slicedStartup[0]; 
    const change = latest - firstInPeriod;
    const pctChange = (change / firstInPeriod) * 100;

    document.getElementById('val-current').innerText = latest.toFixed(2);
    const changeStr = (change >= 0 ? "+" : "") + change.toFixed(2);
    document.getElementById('val-change').innerText = changeStr;
    const pctStr = (pctChange >= 0 ? "+" : "") + pctChange.toFixed(2) + "%";
    document.getElementById('val-pct').innerText = pctStr;
    document.getElementById('title-change').innerText = `${tf} Change`;
    document.getElementById('title-pct').innerText = `${tf} Return`;

    const colorCode = change >= 0 ? 'var(--accent-neon)' : 'var(--accent-red)';
    document.getElementById('val-change').style.color = colorCode;
    document.getElementById('val-pct').style.color = colorCode;

    drawMainChart(slicedDates, slicedStartup, slicedNifty, colorCode);
}

function drawMainChart(labels, startupData, niftyData, lineColor) {
    const ctx = document.getElementById('terminalChart').getContext('2d');
    let gradient = ctx.createLinearGradient(0, 0, 0, 500);
    const rgbColor = lineColor.includes('neon') ? '57, 255, 20' : '255, 80, 0';
    gradient.addColorStop(0, `rgba(${rgbColor}, 0.15)`);
    gradient.addColorStop(1, `rgba(${rgbColor}, 0.0)`);

    if (mainChartInstance) { mainChartInstance.destroy(); }

    mainChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { 
                    label: 'Startup Index', 
                    data: startupData, 
                    borderColor: lineColor, 
                    backgroundColor: gradient, 
                    borderWidth: 2.5, 
                    pointRadius: 0, 
                    pointHoverRadius: 6, 
                    pointHoverBackgroundColor: lineColor, 
                    tension: 0.1, 
                    fill: true 
                },
                { 
                    label: 'NIFTY 50', 
                    data: niftyData, 
                    borderColor: '#444444', 
                    borderWidth: 1.5, 
                    borderDash: [5, 5], 
                    pointRadius: 0, 
                    pointHoverRadius: 0, 
                    tension: 0.1, 
                    fill: false 
                }
            ]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false, 
            interaction: { mode: 'index', intersect: false },
            scales: { 
                x: { 
                    grid: { display: false }, 
                    ticks: { color: '#8a8a93', font: { family: 'Space Grotesk' }, maxTicksLimit: 6 } 
                }, 
                y: { 
                    grid: { color: '#111111' }, 
                    ticks: { color: '#8a8a93', font: { family: 'Space Grotesk' } } 
                }
            },
            plugins: { 
                legend: { display: false }, 
                tooltip: { 
                    backgroundColor: '#111', 
                    titleColor: '#8a8a93', 
                    bodyColor: '#fff', 
                    titleFont: { family: 'Space Grotesk' }, 
                    bodyFont: { family: 'Space Grotesk', size: 14 }, 
                    padding: 15, 
                    cornerRadius: 8, 
                    displayColors: false, 
                    callbacks: { 
                        label: function(context) { 
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2); 
                        } 
                    } 
                } 
            }
        } // <--- This was the missing brace causing the error!
    });
}

function draw52WeekChart(data) {
    const ctx = document.getElementById('fiftyTwoWeekChart').getContext('2d');
    
    const startVal = data.startup_index[0];
    const endVal = data.startup_index[data.startup_index.length - 1];
    const lineColor = endVal >= startVal ? 'var(--accent-neon)' : 'var(--accent-red)';
    const rgbColor = endVal >= startVal ? '57, 255, 20' : '255, 80, 0';

    let gradient = ctx.createLinearGradient(0, 0, 0, 350);
    // High opacity for better visibility
    gradient.addColorStop(0, `rgba(${rgbColor}, 0.5)`);
    gradient.addColorStop(1, `rgba(${rgbColor}, 0.0)`);

    if (fiftyTwoWeekChartInstance) { fiftyTwoWeekChartInstance.destroy(); }

    fiftyTwoWeekChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Index Value', // Added label for the tooltip
                data: data.startup_index,
                borderColor: lineColor,
                backgroundColor: gradient,
                borderWidth: 2, 
                // Enable point radius on hover for that "snapping" feel
                pointRadius: 0, 
                pointHoverRadius: 6,
                pointHoverBackgroundColor: lineColor,
                tension: 0.1, 
                fill: true
            }]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            // 1. ENABLE INTERACTION (Vertical Line)
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: { 
                legend: { display: false }, 
                // 2. ENABLE TOOLTIPS (Copied style from main chart)
                tooltip: { 
                    enabled: true,
                    backgroundColor: '#111', 
                    titleColor: '#8a8a93', 
                    bodyColor: '#fff', 
                    titleFont: { family: 'Space Grotesk' }, 
                    bodyFont: { family: 'Space Grotesk', size: 14 }, 
                    padding: 15, 
                    cornerRadius: 8, 
                    displayColors: false, 
                    callbacks: { 
                        label: function(context) { 
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2); 
                        } 
                    } 
                } 
            }, 
            scales: {
                // Keep the axes hidden for the clean look, but the data is still there for the tooltip
                x: { grid: { display: false }, ticks: { display: false } }, 
                y: { grid: { display: false }, ticks: { display: false } }  
            }
        }
    });
}

// --- NEW REAL DATA FETCHER ---
async function fetchCompositionData() {
    try {
        const response = await fetch('/api/startups/composition');
        if (!response.ok) throw new Error("Network response was not ok");
        
        const stocks = await response.json();
        const grid = document.getElementById('comp-grid');
        let htmlContent = '';

        stocks.forEach(stock => {
            // Safe Data Object for Modal
            const dataObj = {
                name: stock.name,
                mktCap: `Rs. ${stock.mkt_cap.toLocaleString()} Cr`,
                price: `Rs. ${stock.price}`,
                high: `Rs. ${stock.high}`,
                low: `Rs. ${stock.low}`,
                sector: stock.sector,
                weight: `${stock.weight}%`
            };
            const safeDataStr = JSON.stringify(dataObj).replace(/"/g, '&quot;');

            htmlContent += `
            <div class="comp-card" onclick="openModal('stock', ${safeDataStr})">
                <div class="comp-ticker">${stock.ticker}</div>
                <div class="comp-name">${stock.name}</div>
                <div class="comp-stats">
                    <div><span class="c-stat-val">Rs. ${stock.price}</span><br><span class="c-stat-lbl">Price</span></div>
                        <div><span class="c-stat-val" style="color:var(--accent-neon);">${stock.weight}%</span><br><span class="c-stat-lbl">Weight</span></div>
                </div>
            </div>
            `;
        });
        grid.innerHTML = htmlContent;

    } catch (error) {
        console.error("Error fetching composition:", error);
    }
}

// --- INITIALIZATION ---
console.log("System Initializing...");

document.querySelectorAll('.tf-btn').forEach(button => {
    button.addEventListener('click', (e) => {
        document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        currentTimeframe = e.target.getAttribute('data-tf');
        renderTimeframe(currentTimeframe);
    });
});

generateDummyIPOs();
// REMOVE: generateDummyComposition(); 
// ADD:
fetchCompositionData(); 

fetchMarketData();
autoRefreshInterval = setInterval(() => fetchMarketData(), 60000);