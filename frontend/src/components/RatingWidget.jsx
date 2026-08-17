import { useState } from 'react';
import api from '../api';

export default function RatingWidget({ pgId, averageRating, ratingCount, onUpdate }) {
  const [selected, setSelected] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [toast, setToast] = useState('');
  const [toastError, setToastError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!selected) {
      setToast('Please select a star rating first!');
      setToastError(true);
      return;
    }
    setSubmitting(true);
    setToast('');
    try {
      const { data } = await api.post('/rate-pg', { pg_id: pgId, rating: selected });
      if (data.success) {
        setToast('✓ Thanks! Your rating has been saved.');
        setToastError(false);
        setSelected(0);
        if (onUpdate) onUpdate(data.average_rating, data.rating_count);
      }
    } catch {
      setToast('Network error. Please try again.');
      setToastError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rating-widget">
      <div className="rating-widget-header">
        <span className="rating-widget-title">Rate This PG</span>
        <div className="rating-avg-display">
          <span className="rating-avg-num">{averageRating.toFixed(1)}</span>
          <span className="rating-count-label">/ 5 &nbsp;·&nbsp; {ratingCount} rating{ratingCount !== 1 ? 's' : ''}</span>
        </div>
      </div>
      <div className="star-picker">
        {[1, 2, 3, 4, 5].map((val) => (
          <span
            key={val}
            className={`sp-star ${val <= hovered ? 'hovered' : ''} ${val <= selected ? 'selected' : ''}`}
            data-val={val}
            onMouseEnter={() => setHovered(val)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => setSelected(val)}
          >
            ★
          </span>
        ))}
        <button
          className="submit-rating-btn"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? '…' : 'Submit'}
        </button>
      </div>
      <div className={`rating-toast ${toastError ? 'error' : ''}`}>{toast}</div>
    </div>
  );
}
