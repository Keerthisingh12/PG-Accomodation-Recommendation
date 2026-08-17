import { useState } from 'react';

const LOCATIONS = [
  'Hebbal', 'Yelahanka', 'Kalyan Nagar', 'Hennur',
  'Thanisandra', 'Kogilu', 'Jakkur', 'RT Nagar',
];

export default function PreferenceForm({ onSubmit, loading }) {
  const [budget, setBudget] = useState(15000);
  const [form, setForm] = useState({
    location: '',
    gender: '2',
    sharing: 'Any',
    meals: '2',
    wifi: false,
    ac: false,
    laundry: false,
    food: false,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      budget: Number(budget),
      location: form.location,
      gender: Number(form.gender),
      sharing: form.sharing,
      meals: Number(form.meals),
      wifi: form.wifi ? 1 : 0,
      ac: form.ac ? 1 : 0,
      laundry: form.laundry ? 1 : 0,
      food: form.food ? 1 : 0,
    });
  };

  const formatInr = (val) => {
    return '₹' + Number(val).toLocaleString('en-IN');
  };

  return (
    <div className="form-card">
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="section-label">Budget &amp; Location</div>

          <div className="field full">
            <label>Monthly Budget</label>
            <div className="budget-row">
              <input
                type="range"
                min="1000"
                max="20000"
                step="500"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
              />
              <span className="budget-display">{formatInr(budget)}</span>
            </div>
          </div>

          <div className="field">
            <label>Preferred Location</label>
            <input
              type="text"
              name="location"
              placeholder="e.g. Hebbal, Yelahanka…"
              list="location-list"
              value={form.location}
              onChange={handleChange}
            />
            <datalist id="location-list">
              {LOCATIONS.map((loc) => (
                <option key={loc} value={loc} />
              ))}
            </datalist>
          </div>

          <div className="field">
            <label>Gender Preference</label>
            <select name="gender" value={form.gender} onChange={handleChange}>
              <option value="0">👨 Boys Only</option>
              <option value="1">👩 Girls Only</option>
              <option value="2">🤝 Co-ed / Any</option>
            </select>
          </div>

          <div className="field">
            <label>Room Sharing</label>
            <select name="sharing" value={form.sharing} onChange={handleChange}>
              <option value="Any">🛏️ Any</option>
              <option value="Single">👤 Single</option>
              <option value="Double">👥 Double</option>
              <option value="Triple">👨‍👨‍👦 Triple</option>
            </select>
          </div>

          <div className="section-label">Meals</div>

          <div className="field">
            <label>Meals Per Day</label>
            <select name="meals" value={form.meals} onChange={handleChange}>
              <option value="2">2 Meals/day</option>
              <option value="3">3 Meals/day</option>
            </select>
          </div>

          <div className="section-label">Required Amenities</div>

          <div className="chip-group">
            {[
              { id: 'wifi', label: '📶 WiFi' },
              { id: 'ac', label: '❄️ AC' },
              { id: 'laundry', label: '🫧 Laundry' },
              { id: 'food', label: '🍱 Weekend Food' },
            ].map((chip) => (
              <div className="chip" key={chip.id}>
                <input
                  type="checkbox"
                  id={chip.id}
                  name={chip.id}
                  checked={form[chip.id]}
                  onChange={handleChange}
                />
                <label htmlFor={chip.id}>{chip.label}</label>
              </div>
            ))}
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? (
              <><span className="loading-spinner" /> Finding PGs…</>
            ) : (
              <><svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>Find My Best PGs</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
