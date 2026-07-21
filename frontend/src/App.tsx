import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, TrendingUp, Ship, AlertTriangle, CheckCircle, Clock, Database } from 'lucide-react';
import { ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import MapComponent from './MapComponent';

const GuideModal = ({ onClose }: { onClose: () => void }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
    <div className="bg-zinc-900 border border-zinc-700 p-8 max-w-2xl w-full text-zinc-300 relative max-h-[90vh] overflow-y-auto">
      <button onClick={onClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white">✕</button>
      <h2 className="text-2xl font-bold text-white mb-4 uppercase tracking-widest">What is Rakshak AI?</h2>
      <div className="space-y-4 text-sm leading-relaxed">
        <p>Imagine a smart assistant that watches the world's news and shipping data 24/7. If a war or crisis breaks out that might block India's oil supply, <strong>Rakshak AI</strong> acts instantly to protect our economy.</p>
        
        <p>It does this in 4 simple steps:</p>
        
        <ul className="list-decimal pl-5 space-y-2 mb-4">
          <li><strong>Watches for Danger:</strong> It reads global news and databases to spot crises. It even shows you exactly what words triggered the alarm (like "Missile" or "Blockade") in the <em>Rules-Based Keyword Evidence</em>.</li>
          <li><strong>Calculates the Damage:</strong> It figures out how much oil prices will spike, how badly it will hurt India's GDP, and how fast our emergency oil reserves (SPR) will drain in the <em>SPR Countdown</em>.</li>
          <li><strong>Finds a New Path:</strong> It looks across the globe (e.g., USA, Brazil) and finds alternative oil suppliers, figuring out the absolute fastest and cheapest new ship routes to India.</li>
          <li><strong>Takes Action:</strong> It writes a simple memo recommending what ships to reroute. A human just clicks <strong>"Approve"</strong> to execute the plan!</li>
        </ul>

        <h3 className="text-white font-bold uppercase tracking-widest mt-6 border-t border-zinc-700 pt-4">How to play with this Dashboard:</h3>
        <ul className="list-disc pl-5 space-y-2">
          <li><strong>Live Mode:</strong> Watch the AI scan the real world right now for any threats.</li>
          <li><strong>Simulate Crisis:</strong> Click this button to pretend a massive war just broke out, and watch the AI instantly reroute the supply chain!</li>
          <li><strong>Custom Scenario:</strong> Want to test your own crisis? Click this to manually dial in a risk score from 0 (Peace) to 100 (Total War).</li>
          <li><strong>Historical Mode:</strong> Replay real past events (like the 2019 Saudi drone attacks) to see how the AI handles known history.</li>
        </ul>
      </div>
    </div>
  </div>
);

const CustomScenarioModal = ({ onClose, onRun }: { onClose: () => void, onRun: (corridor: string, score: number) => void }) => {
  const [c, setC] = useState('hormuz');
  const [s, setS] = useState(80);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-zinc-700 p-8 max-w-md w-full text-zinc-300 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white">✕</button>
        <h2 className="text-xl font-bold text-white mb-6 uppercase tracking-widest">Create Custom Scenario</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-zinc-500 mb-2">Target Corridor</label>
            <select value={c} onChange={(e) => setC(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 px-4 py-2 text-white">
              <option value="hormuz">Strait of Hormuz</option>
              <option value="malacca">Strait of Malacca</option>
              <option value="suez">Suez Canal</option>
            </select>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-widest text-zinc-500 mb-2">Risk Score: {s}/100</label>
            <input type="range" min="0" max="100" value={s} onChange={(e) => setS(parseInt(e.target.value))} className="w-full" />
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>0 (Peace)</span><span>100 (Total War)</span>
            </div>
          </div>
          <button onClick={() => onRun(c, s)} className="w-full bg-zinc-100 text-black font-bold uppercase tracking-widest py-3 mt-4 hover:bg-zinc-300 transition-colors">
            Run Simulation
          </button>
        </div>
      </div>
    </div>
  );
};

export default function App() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useLive, setUseLive] = useState(false);
  const [corridor, setCorridor] = useState('hormuz');
  const [eventScenario, setEventScenario] = useState('abqaiq_2019');
  const [simulateCrisis, setSimulateCrisis] = useState(false);
  
  // New State for Modals & Custom Scenarios
  const [showGuide, setShowGuide] = useState(false);
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customScore, setCustomScore] = useState<number | null>(null);
  
  // State for Human-in-the-Loop Approval
  const [approvedScenario, setApprovedScenario] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setApprovedScenario(null); // Reset on new run
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        let endpoint = useLive 
          ? `${API_BASE_URL}/api/live-status?corridor=${corridor}&simulate_crisis=${simulateCrisis}`
          : `${API_BASE_URL}/api/historical-replay?event_id=${eventScenario}`;
          
        if (useLive && customScore !== null) {
          endpoint += `&custom_score=${customScore}`;
        }
        
        const res = await fetch(endpoint, { signal: controller.signal });
        if (!res.ok) throw new Error('Failed to fetch data');
        const json = await res.json();
        
        if (json.error) throw new Error(json.error);
        
        if (useLive) {
          setData({
            layer1: json.layer1_output,
            layer2: json.layer2_output,
            layer3: json.layer3_output,
            latencies: json.latencies,
            total_elapsed_ms: json.total_elapsed_ms
          });
        } else {
          // Historical files contain an array of "steps". We render the first step (peak crisis).
          setData(json.steps[0]);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          console.log('Fetch aborted');
        } else {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    return () => {
      controller.abort();
    };
  }, [useLive, corridor, eventScenario, simulateCrisis, customScore]);

  const getAlertColor = (level: string) => {
    if (!level) return 'text-zinc-500';
    const l = level.toLowerCase();
    if (l === 'high') return 'text-zinc-200';
    if (l === 'medium') return 'text-zinc-400';
    return 'text-zinc-500';
  };

  // Prepare chart data
  let brentProjections = [];
  let signalData = [];
  
  if (data) {
    brentProjections = data.layer2?.projections?.brent_price_usd?.map((p: any) => ({
      day: `Day ${p.day}`,
      price: p.value,
      range: p.lower !== undefined && p.upper !== undefined 
        ? [p.lower, p.upper] 
        : [parseFloat((p.value * 0.90).toFixed(2)), parseFloat((p.value * 1.15).toFixed(2))]
    })) || [];
    
    const sub = data.layer1?.sub_scores || {};
    signalData = [
      { subject: 'News Sentiment', A: sub.news_sentiment || 0, fullMark: 100 },
      { subject: 'Sanctions Delta', A: sub.sanctions_delta || 0, fullMark: 100 },
      { subject: 'Polymarket', A: sub.prediction_market || 0, fullMark: 100 },
      { subject: 'AIS Gap (Simulated*)', A: sub.ais_dark_fleet || 0, fullMark: 100 },
      { subject: 'Futures Spread', A: sub.futures_spread || 0, fullMark: 100 },
    ];
  }

  return (
    <div className="min-h-screen p-6 relative overflow-hidden bg-black text-zinc-100 font-sans">
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card mb-8 p-8 flex flex-col items-center justify-center z-10 relative border-b-2 border-zinc-700"
      >
        <div className="w-full text-center mb-6">
          <h1 className="text-4xl md:text-6xl font-bold uppercase tracking-[0.2em] md:tracking-[0.5em] text-white glow-text w-full flex justify-between">
            {/* Spreading the text across the space */}
            <span>R</span><span>A</span><span>K</span><span>S</span><span>H</span><span>A</span><span>K</span><span className="ml-4 md:ml-8">A</span><span>I</span>
          </h1>
          <p className="text-zinc-400 font-medium tracking-[0.2em] mt-4 uppercase text-sm border-t border-zinc-800 pt-4 w-full">Strategic Energy Security Intelligence</p>
        </div>
        
        <div className="flex gap-4 w-full justify-center flex-wrap items-center border-t border-zinc-800 pt-6">
          <div className="glass px-4 py-2 flex items-center gap-3 border border-zinc-700">
            <span className="text-sm font-medium text-zinc-400 uppercase tracking-widest">Mode</span>
            <button 
              onClick={() => { setUseLive(false); setCustomScore(null); setSimulateCrisis(false); }}
              className={`px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all border ${!useLive ? 'bg-zinc-800 text-white border-zinc-500' : 'text-zinc-500 border-transparent hover:text-zinc-300'}`}
            >
              Historical
            </button>
            <button 
              onClick={() => { setUseLive(true); setCustomScore(null); setSimulateCrisis(false); }}
              className={`px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all flex items-center gap-2 border ${useLive ? 'bg-zinc-800 text-white border-zinc-500' : 'text-zinc-500 border-transparent hover:text-zinc-300'}`}
            >
              <span className={`w-2 h-2 bg-zinc-300 ${useLive ? 'animate-pulse' : ''}`} /> Live
            </button>
          </div>
          
          {!useLive ? (
            <select 
              value={eventScenario} 
              onChange={(e) => setEventScenario(e.target.value)}
              className="glass px-4 py-2 text-sm text-zinc-300 font-medium uppercase tracking-wider focus:outline-none focus:ring-1 focus:ring-zinc-500 border border-zinc-700 appearance-none cursor-pointer"
            >
              <option value="abqaiq_2019" className="bg-zinc-900 text-white">Abqaiq 2019</option>
              <option value="us_iran_2025" className="bg-zinc-900 text-white">US/Iran 2025</option>
            </select>
          ) : (
            <>
              <select 
                value={corridor} 
                onChange={(e) => { setCorridor(e.target.value); setCustomScore(null); setSimulateCrisis(false); }}
                className="glass px-4 py-2 text-sm text-zinc-300 font-medium uppercase tracking-wider focus:outline-none focus:ring-1 focus:ring-zinc-500 border border-zinc-700 appearance-none cursor-pointer"
              >
                <option value="hormuz" className="bg-zinc-900 text-white">Strait of Hormuz</option>
                <option value="malacca" className="bg-zinc-900 text-white">Strait of Malacca</option>
                <option value="suez" className="bg-zinc-900 text-white">Suez Canal</option>
              </select>
              
              <button 
                onClick={() => {
                  if (simulateCrisis) {
                    setSimulateCrisis(false);
                  } else {
                    setSimulateCrisis(true);
                    setCustomScore(null); // Reset custom score if simulating hardcoded crisis
                  }
                }}
                className={`px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all flex items-center gap-2 border ${simulateCrisis ? 'bg-red-900/50 text-red-400 border-red-500/50' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'}`}
              >
                <AlertTriangle className="w-4 h-4" /> 
                {simulateCrisis ? 'SIMULATION ACTIVE' : 'SIMULATE CRISIS'}
              </button>
            </>
          )}
          
          {/* Custom Scenario Button */}
          <button 
            onClick={() => setShowCustomModal(true)}
            className="px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all flex items-center gap-2 text-zinc-400 border border-zinc-700 hover:text-white hover:bg-zinc-800"
          >
            + CUSTOM SCENARIO
          </button>

          <button 
            onClick={() => setShowGuide(true)}
            className="px-4 py-2 text-sm font-bold uppercase tracking-wider transition-all flex items-center gap-2 text-zinc-400 border border-zinc-700 hover:text-white hover:bg-zinc-800"
          >
          📖 GUIDE
          </button>
        </div>
      </motion.header>

      {/* Historical Validation Banner */}
      {!useLive && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full bg-red-900/40 border border-red-500/50 text-red-400 text-center py-2 mb-6 font-bold uppercase tracking-widest text-sm z-20 relative shadow-[0_0_15px_rgba(239,68,68,0.2)]"
        >
          [ HISTORICAL VALIDATION REPLAY - NOT LIVE DATA ]
        </motion.div>
      )}

      {/* Main Content Dashboard */}
      {loading ? (
        <div className="flex justify-center items-center h-[60vh]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-2 border-zinc-800 border-t-zinc-400 animate-spin" />
            <p className="text-zinc-500 uppercase tracking-widest font-medium text-sm">Processing Data...</p>
          </div>
        </div>
      ) : error ? (
        <div className="glass-card border-zinc-600 p-8 text-center text-zinc-400">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-80" />
          <h2 className="text-xl font-bold mb-2 uppercase tracking-widest">System Error</h2>
          <p className="font-mono">{error}</p>
        </div>
      ) : data ? (
        <AnimatePresence mode="wait">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, staggerChildren: 0.1 }}
            className="space-y-6 relative z-10"
          >
            {/* Top Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <Activity className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Alert Level</span>
                </div>
                <div className="text-3xl font-bold text-white capitalize flex items-center gap-3 tracking-widest">
                  <span className={getAlertColor(data.layer1?.alert_level)}>{data.layer1?.alert_level || 'N/A'}</span>
                  {data.layer1?.alert_level === 'high' && <AlertTriangle className="w-6 h-6 text-zinc-300 animate-pulse" />}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono tracking-widest uppercase">Risk: {data.layer1?.score?.toFixed(1) || 0}/100</p>
              </motion.div>

              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <TrendingUp className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Peak Brent Impact</span>
                </div>
                <div className="text-3xl font-bold text-white flex items-baseline gap-1 tracking-widest">
                  <span className="text-xl text-zinc-600">$</span>
                  {brentProjections.length > 0 ? Math.max(...brentProjections.map(p => p.price)).toFixed(2) : '0.00'}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest truncate" title={data.layer2?.scenario_id}>
                  {data.layer2?.scenario_id?.replace(/_/g, ' ') || 'N/A'}
                </p>
              </motion.div>

              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <Clock className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Confidence</span>
                </div>
                <div className="text-3xl font-bold text-white capitalize tracking-widest">
                  {data.layer2?.confidence || 'N/A'}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest">Trigger: {data.layer1?.corridor || 'N/A'}</p>
              </motion.div>

              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600 relative overflow-hidden group">
                <div className="absolute inset-0 bg-zinc-800/50 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="flex items-center gap-3 mb-2 opacity-60 relative z-10">
                  <Ship className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Options</span>
                </div>
                <div className="text-3xl font-bold text-white relative z-10 tracking-widest">
                  {data.layer3?.recommendations?.length || 0}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest relative z-10">AI Ranked Paths</p>
              </motion.div>
            </div>

            {/* Rules-Based Keyword Evidence */}
            {data.layer1?.evidence && data.layer1.evidence.length > 0 && (
              <motion.div className="glass-card p-6 border-l-4 border-l-blue-500 bg-zinc-900/50 mt-6">
                <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-widest flex items-center gap-2 mb-4 border-b border-zinc-800 pb-2">
                  <Database className="w-4 h-4 text-blue-400" />
                  Rules-Based Keyword Evidence
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {data.layer1.evidence.slice(0, 3).map((item: any, idx: number) => (
                    <div key={idx} className="bg-zinc-800/30 p-4 border border-zinc-700 hover:border-zinc-500 transition-colors flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-[10px] uppercase font-bold tracking-widest text-zinc-500">{item.source}</span>
                          {item.severity_tag && (
                            <span className={`text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 ${
                              item.severity_tag === 'HIGH' ? 'bg-red-900/50 text-red-400 border border-red-800' :
                              item.severity_tag === 'MEDIUM' ? 'bg-orange-900/50 text-orange-400 border border-orange-800' :
                              'bg-zinc-800 text-zinc-400 border border-zinc-700'
                            }`}>
                              {item.severity_tag}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                          "{item.summary}"
                        </p>
                      </div>
                      {item.extracted_keywords && item.extracted_keywords.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {item.extracted_keywords.map((kw: string, kidx: number) => (
                            <span key={kidx} className="text-[9px] bg-blue-900/30 text-blue-400 border border-blue-800/50 px-1.5 py-0.5 uppercase tracking-wider">
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Map */}
              <motion.div className="glass-card p-0 overflow-hidden relative border-t border-zinc-600 flex flex-col">
                <div className="p-4 border-b border-zinc-800 bg-zinc-900/80 z-10 absolute top-0 left-0 right-0">
                  <h3 className="text-sm font-bold text-zinc-300 flex items-center gap-3 uppercase tracking-widest">
                    <div className="w-2 h-2 bg-zinc-500" />
                    Geospatial Context
                  </h3>
                </div>
                <div className="glass-card p-2 h-[400px] mt-6 border-b-4 border-b-zinc-800">
                  <MapComponent 
                    corridor={data.layer1?.corridor} 
                    routes={data.layer3?.recommendations} 
                    approved={approvedScenario === data.layer2?.scenario_id}
                  />
                </div>
              </motion.div>

              {/* Radar Chart */}
              <motion.div className="glass-card p-6 border-t border-zinc-600">
                <h3 className="text-sm font-bold text-zinc-300 mb-6 flex items-center gap-3 uppercase tracking-widest border-b border-zinc-800 pb-4">
                  <div className="w-2 h-2 bg-zinc-500" />
                  Layer 1: Vectors
                </h3>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="75%" data={signalData}>
                      <PolarGrid stroke="rgba(255,255,255,0.1)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'monospace' }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar name="Signal Strength" dataKey="A" stroke="#71717a" fill="#3f3f46" fillOpacity={0.5} />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '0px', fontFamily: 'monospace', fontSize: '12px' }} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>

              {/* Line Chart */}
              <motion.div className="glass-card p-6 border-t border-zinc-600">
                <h3 className="text-sm font-bold text-zinc-300 mb-6 flex items-center gap-3 uppercase tracking-widest border-b border-zinc-800 pb-4">
                  <div className="w-2 h-2 bg-zinc-500" />
                  Layer 2: Price (14D)
                </h3>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={brentProjections} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.05)" vertical={false} />
                      <XAxis dataKey="day" stroke="rgba(255,255,255,0.2)" tick={{fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'monospace'}} />
                      <YAxis stroke="rgba(255,255,255,0.2)" tick={{fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'monospace'}} domain={['auto', 'auto']} tickFormatter={(val) => `$${val}`} />
                      <RechartsTooltip 
                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '0px', fontFamily: 'monospace', fontSize: '12px' }}
                        itemStyle={{ color: '#d4d4d8' }}
                        formatter={(value: any, name: any) => name === 'range' ? null : [`$${value.toFixed(2)}`, 'Brent Price']}
                      />
                      <Area type="stepAfter" dataKey="range" stroke="none" fill="#ef4444" fillOpacity={0.15} />
                      <Line type="stepAfter" dataKey="price" stroke="#a1a1aa" strokeWidth={2} dot={{ r: 0 }} activeDot={{ r: 4, fill: '#fff', stroke: '#000' }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            </div>

            {/* Macroeconomic Impact Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <Activity className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">GDP Drag (Est)</span>
                </div>
                <div className="text-3xl font-bold text-red-400 tracking-widest">
                  -{data.layer2?.projections?.gdp_drag_pct?.toFixed(2) || '0.00'}%
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest">National Economic Impact</p>
              </motion.div>

              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <TrendingUp className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Peak Fuel Price</span>
                </div>
                <div className="text-3xl font-bold text-orange-400 flex items-baseline gap-1 tracking-widest">
                  <span className="text-xl text-zinc-600">₹</span>
                  {data.layer2?.projections?.domestic_fuel_price_inr_per_liter ? 
                    Math.max(...data.layer2.projections.domestic_fuel_price_inr_per_liter.map((p: any) => p.value)).toFixed(1) 
                    : '0.0'}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest">INR per Liter (Projected) <br/><span className="text-[10px] opacity-70">(DELHI BENCHMARK)</span></p>
              </motion.div>

              <motion.div className="glass-card p-6 flex flex-col justify-center border-t border-zinc-600">
                <div className="flex items-center gap-3 mb-2 opacity-60">
                  <TrendingUp className="w-4 h-4 text-zinc-400" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-400">Peak INR/USD</span>
                </div>
                <div className="text-3xl font-bold text-yellow-400 flex items-baseline gap-1 tracking-widest">
                  <span className="text-xl text-zinc-600">₹</span>
                  {data.layer2?.projections?.inr_usd_rate ? 
                    Math.max(...data.layer2.projections.inr_usd_rate.map((p: any) => p.value)).toFixed(2) 
                    : '0.00'}
                </div>
                <p className="mt-2 text-xs text-zinc-500 font-mono uppercase tracking-widest">Exchange Rate Depreciation</p>
              </motion.div>
            </div>

            {/* Strategic Petroleum Reserve (SPR) Countdown */}
            {data.layer2?.projections?.spr_depletion && (
              <motion.div className="glass-card p-6 mt-6 border border-red-900/30 bg-gradient-to-r from-red-950/20 to-black relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-zinc-800">
                  <div 
                    className="h-full bg-red-500 transition-all duration-1000" 
                    style={{ width: `${(data.layer2.projections.spr_depletion.days_remaining / 9.5) * 100}%` }}
                  />
                </div>
                <div className="flex flex-col md:flex-row justify-between items-center gap-6 relative z-10">
                  <div>
                    <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-widest flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-red-400" />
                      Strategic Petroleum Reserve (SPR) Countdown
                    </h3>
                    <p className="text-zinc-400 text-sm max-w-2xl">
                      At current disruption severity, India's {data.layer2.projections.spr_depletion.base_days_of_cover}-day national buffer depletes in <strong>{data.layer2.projections.spr_depletion.days_remaining} days</strong>. 
                      Drawdown rate is accelerated by <strong>{data.layer2.projections.spr_depletion.drawdown_multiplier}x</strong> (dynamically based on live risk score &gt; 50) as refiners tap reserves to cover the supply gap.
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-5xl font-black text-red-500 tracking-tighter">
                      {data.layer2.projections.spr_depletion.days_remaining} <span className="text-xl text-zinc-500 uppercase tracking-widest font-bold">Days</span>
                    </div>
                    <div className="text-xs text-zinc-500 uppercase tracking-widest mt-1">Remaining Cover</div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Agentic Memo / Human-in-the-Loop */}
            {data.layer3?.recommendations?.length > 0 && (
              <motion.div className="glass-card p-6 mt-6 mb-6 border border-zinc-700 bg-zinc-900/50 relative overflow-hidden">
                <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-widest flex items-center gap-2 mb-4 border-b border-zinc-800 pb-2">
                  <Activity className="w-4 h-4 text-zinc-400" />
                  Procurement Action Plan
                </h3>
                
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                  <div className="flex-1">
                    <p className="text-zinc-200 text-lg font-mono">
                      "Reroute {data.layer3.recommendations[0].tanker_class || 'available'} shipments from <strong>{data.layer1?.corridor?.toUpperCase() || 'PRIMARY'}</strong>-transit supplier to <strong>{data.layer3.recommendations[0].source_supplier || 'alternative'}</strong>. 
                      Expected cost delta <strong>+{data.layer3.recommendations[0].cost_delta_vs_baseline_pct || 0}%</strong>, 
                      execute within <strong>{data.layer3.recommendations[0].time_to_execute_hours || 'TBD'} hrs</strong>."
                    </p>
                    {approvedScenario === data.layer2?.scenario_id && (
                      <div className="mt-3 text-xs text-green-400 font-bold uppercase tracking-widest flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" /> Action Logged: {new Date().toISOString()}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-3">
                    <button 
                      onClick={() => setApprovedScenario(data.layer2?.scenario_id)}
                      disabled={approvedScenario === data.layer2?.scenario_id}
                      className={`px-6 py-3 font-bold uppercase tracking-widest text-xs transition-colors ${
                        approvedScenario === data.layer2?.scenario_id 
                        ? 'bg-green-900/50 text-green-400 border border-green-800 cursor-not-allowed'
                        : 'bg-zinc-100 text-black hover:bg-zinc-300'
                      }`}
                    >
                      {approvedScenario === data.layer2?.scenario_id ? 'Approved' : 'Approve'}
                    </button>
                    <button 
                      disabled={approvedScenario === data.layer2?.scenario_id}
                      className="px-6 py-3 font-bold uppercase tracking-widest text-xs border border-zinc-700 text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Recommendations Table */}
            <motion.div className="glass-card p-6 overflow-hidden">
              <h3 className="text-sm font-bold text-zinc-300 mb-6 flex items-center gap-3 uppercase tracking-widest border-b border-zinc-800 pb-4">
                <div className="w-2 h-2 bg-zinc-500" />
                Layer 3: Ranked Sourcing
              </h3>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse font-mono text-sm">
                  <thead>
                    <tr className="border-b border-zinc-700 text-zinc-500 uppercase tracking-widest">
                      <th className="py-4 px-4 font-normal">Rank</th>
                      <th className="py-4 px-4 font-normal">Supplier</th>
                      <th className="py-4 px-4 font-normal">Logistics</th>
                      <th className="py-4 px-4 font-normal">Spot Price</th>
                      <th className="py-4 px-4 font-normal">Time</th>
                      <th className="py-4 px-4 font-normal">Friction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.layer3?.recommendations?.map((rec: any, idx: number) => (
                      <motion.tr 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.05 * idx }}
                        key={idx} 
                        className={`border-b border-zinc-800 hover:bg-zinc-800/50 transition-colors ${idx === 0 ? 'bg-zinc-900 border-l-2 border-l-zinc-300' : 'border-l-2 border-l-transparent'}`}
                      >
                        <td className="py-4 px-4 text-zinc-300">
                          [{rec.rank}]
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-zinc-200 uppercase tracking-wide">{rec.source_supplier}</div>
                          <div className="text-xs text-zinc-600 mt-1 flex items-center gap-1 uppercase">
                            <CheckCircle className="w-3 h-3 text-zinc-500" /> MATCH
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-zinc-400 uppercase leading-relaxed">{rec.route}</div>
                          <div className="text-xs text-zinc-600 mt-1 uppercase">{rec.tanker_class} | {rec.tanker_availability}</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-zinc-100">${rec.spot_price_usd_per_bbl?.toFixed(2)}</div>
                          <div className="text-xs mt-1 text-zinc-500">
                            {rec.cost_delta_vs_baseline_pct > 0 ? '+' : ''}{rec.cost_delta_vs_baseline_pct}%
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-zinc-300">{Math.round(rec.time_to_execute_hours / 24)}D</div>
                          <div className="text-xs text-zinc-600 mt-1 uppercase">{rec.time_to_execute_hours}H</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex gap-2 text-xs uppercase tracking-wider">
                            <span className="border border-zinc-600 px-2 py-1 text-zinc-400">
                              {rec.relationship_cost}
                            </span>
                            <span className="border border-zinc-600 px-2 py-1 text-zinc-400">
                              {rec.port_congestion_factor}
                            </span>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </motion.div>
        </AnimatePresence>
      ) : null}
      
      {/* Footer / Latency Metrics */}
      {data && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 border-t border-zinc-800 pt-4 flex flex-col md:flex-row justify-between items-center text-xs font-mono uppercase tracking-widest text-zinc-600 gap-4"
        >
          <div className="flex gap-6">
            <span>Layer 1 (Ingest): {data.latencies?.layer1_ingest_ms?.toFixed(1) || 0}ms</span>
            <span>Layer 2 (Model): {data.latencies?.layer2_process_ms?.toFixed(1) || 0}ms</span>
            <span>Layer 3 (Route): {data.latencies?.layer3_process_ms?.toFixed(1) || 0}ms</span>
          </div>
          <div className="text-zinc-400 font-bold border border-zinc-700 px-3 py-1 bg-zinc-900/50">
            End-to-End Latency: {data.total_elapsed_ms?.toFixed(1) || 0}ms
          </div>
        </motion.div>
      )}

      {showGuide && <GuideModal onClose={() => setShowGuide(false)} />}
      {showCustomModal && (
        <CustomScenarioModal 
          onClose={() => setShowCustomModal(false)} 
          onRun={(c, s) => { 
            setUseLive(true); 
            setCorridor(c); 
            setCustomScore(s); 
            setSimulateCrisis(false); 
            setShowCustomModal(false); 
          }} 
        />
      )}
    </div>
  );
}
