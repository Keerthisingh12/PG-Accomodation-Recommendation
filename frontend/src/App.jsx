import { useState } from 'react';
import api from './api';
import Hero from './components/Hero';
import PreferenceForm from './components/PreferenceForm';
import UserSummary from './components/UserSummary';
import StatsBar from './components/StatsBar';
import EmptyState from './components/EmptyState';
import PGCard from './components/PGCard';
import './App.css';

export default function App() {
  const [results, setResults] = useState(null);
  const [userPrefs, setUserPrefs] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError('');
    setResults(null);
    setUserPrefs(formData);
    setSubmitted(true);

    try {
      const { data } = await api.post('/recommendations', formData);
      if (data.error) {
        setError(data.error);
        setResults(null);
      } else {
        setResults(data.results || []);
      }
    } catch (err) {
      if (err.response?.status === 503) {
        setError('ML service is not available. Please ensure the recommendation engine is running.');
      } else {
        setError('Something went wrong. Please try again.');
      }
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="page-wrap">
        <Hero />

        <PreferenceForm onSubmit={handleSubmit} loading={loading} />

        {results && results.length > 0 && <UserSummary user={userPrefs} />}

        {results && results.length > 0 && <StatsBar results={results} />}

        {results && results.length > 0 && (
          <div className="results-header">
            <span>Your Recommendations</span>
            <span className="results-count">{results.length} found</span>
          </div>
        )}

        {results && results.length > 0 && (
          <div className="results-grid">
            {results.map((pg) => (
              <PGCard key={pg.PG_ID || pg.Rank} pg={pg} />
            ))}
          </div>
        )}

        {(error || (submitted && results && results.length === 0)) && (
          <EmptyState error={error} />
        )}

        <footer>
          PG Finder · Bangalore North · Built with ❤️ for smarter house-hunting
        </footer>
      </div>
    </>
  );
}
