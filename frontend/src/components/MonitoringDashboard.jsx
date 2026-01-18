import { useState, useEffect } from 'react';
import { api } from '../api';
import './MonitoringDashboard.css';

export default function MonitoringDashboard({ onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      const result = await api.getMonitoringData();
      setData(result);
      setError(null);
    } catch (err) {
      setError('Failed to fetch monitoring data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) return <div className="monitoring-loading">Loading monitoring data...</div>;

  return (
    <div className="monitoring-dashboard">
      <div className="monitoring-header">
        <h1>System Monitoring</h1>
        <button className="close-btn" onClick={onClose}>Close</button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {data && (
        <div className="monitoring-content">
          <div className="status-card">
            <h2>Ollama Service</h2>
            <div className={`status-indicator ${data.status.service}`}>
              <span className="status-dot"></span>
              <span className="status-text">{data.status.service.toUpperCase()}</span>
            </div>
            <div className="status-details">
              <p><strong>Version:</strong> {data.status.version}</p>
            </div>
          </div>

          <div className="stats-card">
            <h2>Global Performance</h2>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-value">{data.stats.global.total_requests}</span>
                <span className="stat-label">Total Requests</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{data.stats.global.failed_requests}</span>
                <span className="stat-label">Failed</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{data.stats.global.average_latency_ms}ms</span>
                <span className="stat-label">Avg Latency</span>
              </div>
            </div>
          </div>

          <div className="models-card">
            <h2>Running Models</h2>
            {data.status.running_models.length === 0 ? (
              <p className="no-data">No models currently loaded in memory.</p>
            ) : (
              <ul className="models-list">
                {data.status.running_models.map((model, idx) => (
                  <li key={idx} className="model-item">
                    <span className="model-name">{model.name}</span>
                    <span className="model-size">{(model.size / 1024 / 1024 / 1024).toFixed(2)} GB</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="usage-card">
            <h2>Model Usage Stats</h2>
            {Object.keys(data.stats.models).length === 0 ? (
              <p className="no-data">No usage data yet.</p>
            ) : (
              <table className="usage-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Requests</th>
                    <th>Errors</th>
                    <th>Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.stats.models).map(([name, stats]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>{stats.count}</td>
                      <td>{stats.errors}</td>
                      <td>{stats.average_latency_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
