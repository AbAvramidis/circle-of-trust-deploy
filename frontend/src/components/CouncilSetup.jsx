import { useState, useEffect } from 'react';
import { api } from '../api';
import './CouncilSetup.css';

export default function CouncilSetup({ onComplete }) {
  const [advisors, setAdvisors] = useState(Array(5).fill({ name: '', description: '', model: '' }));
  const [availableModels, setAvailableModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [modelsRes, configRes] = await Promise.all([
          api.listModels(),
          api.getCouncilConfig()
        ]);
        
        setAvailableModels(modelsRes.models || []);
        
        if (configRes.advisors && configRes.advisors.length > 0) {
          // Pad with empty if less than 5, or slice if more (though backend enforces 5 usually)
          const loadedAdvisors = configRes.advisors.slice(0, 5).map(a => ({
            name: a.name || '',
            description: a.description || '',
            model: a.model || ''
          }));
          while (loadedAdvisors.length < 5) {
            loadedAdvisors.push({ name: '', description: '', model: '' });
          }
          setAdvisors(loadedAdvisors);
        } else {
            // Default state if no config
             setAdvisors(Array(5).fill({ name: '', description: '', model: '' }));
        }
      } catch (error) {
        console.error("Failed to load setup data", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleChange = (index, field, value) => {
    const newAdvisors = [...advisors];
    newAdvisors[index] = { ...newAdvisors[index], [field]: value };
    setAdvisors(newAdvisors);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    
    // Filter out empty rows? Or require all 5? 
    // User said "Every user has 5 choices. It could be less but not more than that."
    // Let's filter out completely empty ones, but maybe require at least 1?
    const validAdvisors = advisors.filter(a => a.name.trim() !== '');
    
    if (validAdvisors.length === 0) {
        alert("Please define at least one advisor.");
        setIsSaving(false);
        return;
    }

    try {
      await api.updateCouncilConfig(validAdvisors);
      onComplete();
    } catch (error) {
      console.error("Failed to save council config", error);
      alert("Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <div className="setup-loading">Loading configuration...</div>;

  return (
    <div className="council-setup">
      <div className="council-setup-container">
        <h1>Define Your Circle of Trust</h1>
        <p>Choose up to 5 advisors. We will generate their personas for you.</p>
        
        <form onSubmit={handleSubmit}>
          <div className="advisors-grid">
            {advisors.map((advisor, index) => (
              <div key={index} className="advisor-card">
                <h3>Advisor {index + 1}</h3>
                
                <div className="form-group">
                  <label>Name</label>
                  <input 
                    type="text" 
                    value={advisor.name} 
                    onChange={(e) => handleChange(index, 'name', e.target.value)}
                    placeholder="e.g. Albert Einstein"
                    required={index === 0} // Require at least the first one?
                  />
                </div>
                
                <div className="form-group">
                  <label>Description / Role</label>
                  <textarea 
                    value={advisor.description || ''} 
                    onChange={(e) => handleChange(index, 'description', e.target.value)}
                    placeholder="e.g. Theoretical Physicist, focus on relativity..."
                    rows={2}
                  />
                </div>
                
                <div className="form-group">
                  <label>Model</label>
                  <select 
                    value={advisor.model} 
                    onChange={(e) => handleChange(index, 'model', e.target.value)}
                  >
                    <option value="">Select a model...</option>
                    {availableModels.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
          
          <div className="actions">
            <button type="submit" className="save-button" disabled={isSaving}>
              {isSaving ? 'Generating Personas...' : 'Create Council'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
