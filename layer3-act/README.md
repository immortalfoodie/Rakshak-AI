# Rakshak AI - Layer 3 (Act) Component

Welcome to the **layer3-act** component of Rakshak AI! 

This component helps India respond to crude oil supply chain disruptions (specifically in the Strait of Hormuz). It takes a projected supply disruption scenario (from the upstream Layer 2 scenario model) and automatically generates a ranked list of alternative crude oil sourcing options and shipping routes. These recommendations are tailored to the configuration of India's refiners.

---

## 📁 File Descriptions (in Plain Language)

Here is what each file in this folder does:

1. **`requirements.txt`**:
   - A list of Python libraries (helper software) that our script needs to run. It includes `jsonschema` (to double-check that our data files match the strict formats required by other components) and `tabulate` (to print beautiful tables in your terminal).

2. **`refineries.json`**:
   - A configuration file containing profiles of major Indian refineries (like Jamnagar, Vadinar, and Paradip). It maps each refinery to its crude grade capabilities. Some refineries can process both "sour" (high sulfur) and "sweet" (low sulfur) crude, while others (like Digboi) can only process "sweet" crude. This is used to ensure we never recommend crude that a refinery cannot physically process.

3. **`routes.json`**:
   - A database of 10 real-world alternative crude oil sourcing options (e.g. US, Brazil, Nigeria, Angola, Russia, Saudi Arabia via Yanbu, UAE via Fujairah). It stores information like the exact route, distances, tanker sizes, shipping lead times, standard prices, and political relationships.

4. **`rank_sourcing.py`**:
   - The main brain of this component. This Python script loads the disruption details, filters out incompatible crude types for your chosen refinery, calculates real-time delivered spot prices (factoring in distance, tanker size, and war risk premiums), runs the ranking math, writes out the final JSON file, and displays the recommendations in a clean table.

5. **`README.md`**:
   - This documentation file you are reading right now!

---

## 📈 How the Sourcing & Ranking Math Works

Our ranking system uses a weighted multi-criteria decision model. Every compatible route is scored out of **100 points** based on four criteria:

1. **Refinery Compatibility (Hard Filter)**:
   - If the alternative crude grade is not compatible with the selected refinery (e.g., trying to feed sour crude into the sweet-only Digboi refinery), the option is immediately excluded from the list.

2. **Delivered Cost (40% Weight)**:
   - **Math**: `Delivered Spot Price = Brent Price + Grade Differential + Freight Cost + Risk Premium`
     - *Grade Differential*: The premium or discount of that specific crude type relative to Brent (e.g., Russia Urals has a large -$8.00 discount).
     - *Freight Cost*: Calculated using real shipping distances and tanker fuel/operating costs. VLCCs (very large tankers) are the most cost-effective per barrel, while Aframaxes (smaller tankers) are the most expensive.
     - *Risk Premium*: If a route must go through the Strait of Hormuz during a disruption, we add a heavy premium (up to $15.00/bbl depending on the severity) to cover war risk insurance and freight spikes.
   - **Scoring**: A cost delta is calculated against a pre-disruption baseline. Every 1% price increase reduces the cost score by 3 points.

3. **Time to Execute (20% Weight)**:
   - **Math**: `Time to Act = Tanker Charter Lead Time + (Distance / 14 Knots Speed) + Port Congestion Delay`
     - If the route goes through the disrupted Strait of Hormuz, we add a severe traffic delay (up to an extra 7 days) to reflect the corridor crisis.
   - **Scoring**: Shorter timelines are better. Every day of delay reduces the time score by 2 points.

4. **Diversification Value (25% Weight)**:
   - Evaluates how much the route reduces India's concentration risk:
     - **High (100 points)**: Atlantic/Western hemisphere crudes (e.g., US WTI, Nigeria, Brazil) that completely bypass Middle East choke points.
     - **Medium (60 points)**: Middle East crudes loaded from ports outside the Persian Gulf (e.g., UAE via Fujairah, Saudi Arabia via Yanbu).
     - **Low (20 points)**: Routes that still have to transit the Strait of Hormuz (e.g., Iraq Basra).

5. **Relationship & Geopolitical Cost (15% Weight)**:
   - Reflects the diplomatic and operational friction of using each source:
     - **Low Friction (100 points)**: Established suppliers with active long-term contracts (e.g., Saudi, UAE, US).
     - **Medium Friction (60 points)**: Friendly spot market suppliers requiring new contracts (e.g., Angola, Russia ESPO).
     - **High Friction (20 points)**: Geopolitically sensitive or heavily sanctioned options (e.g., Russian Urals requiring price cap enforcement and banking workarounds).

---

## 🚀 How to Run and Test the Code

### 1. Set Up Your Environment
Before running the script, make sure your dependencies are installed. In your terminal, run:
```powershell
pip install -r layer3-act/requirements.txt
```

### 2. Test Against the Mock Input (Default Jamnagar Refinery)
To test the script using the default configuration (for the complex, sour-optimized **Jamnagar** refinery), run:
```powershell
python layer3-act/rank_sourcing.py
```
This will read `shared/sample_data/mock_layer2_output.json`, perform the ranking, print a table in the terminal, and save the schema-compliant output to `shared/sample_data/mock_layer3_output.json`.

### 3. Test a Sweet-Only Refinery (Testing the Grade Filter)
To run the analysis for **Digboi**, India's oldest refinery that can only process **sweet** crude, run:
```powershell
python layer3-act/rank_sourcing.py --refinery Digboi
```
You will notice that all sour options (like Saudi Arab Light, Russia Urals, UAE Murban, and Iraq Basra) are filtered out, and only sweet options (like US WTI, Nigeria Bonny Light, Brazil Tupi, and Russian ESPO) are ranked!

### 4. Customizing the Weights
If you want to prioritize speed over cost (e.g., during an extreme emergency where getting oil immediately is more important than price), you can adjust the scoring weights using the CLI flags:
```powershell
python layer3-act/rank_sourcing.py --cost-weight 0.10 --time-weight 0.60 --diversification-weight 0.20 --relationship-weight 0.10
```
*(Note: The weights should sum to 1.0)*
