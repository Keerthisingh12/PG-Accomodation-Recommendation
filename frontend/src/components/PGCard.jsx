import { useEffect, useRef } from 'react';
import RatingWidget from './RatingWidget';
import ReviewWidget from './ReviewWidget';

const CURFEW_MAP = { 0: '9 PM', 1: '10 PM', 2: '11 PM', 3: 'None' };

const AMENITIES = [
  { key: 'WiFi', label: '📶 WiFi' },
  { key: 'AC', label: '❄️ AC' },
  { key: 'Laundry', label: '🫧 Laundry' },
  { key: 'Parking', label: '🚗 Parking' },
  { key: 'Security', label: '🔒 Security' },
  { key: 'Power_Backup', label: '⚡ Power Backup' },
];

export default function PGCard({ pg }) {
  const fillRef = useRef(null);

  useEffect(() => {
    const el = fillRef.current;
    if (!el) return;
    const target = el.getAttribute('data-target');
    const timer = setTimeout(() => {
      el.style.width = target;
    }, 200);
    return () => clearTimeout(timer);
  }, [pg.PG_ID]);

  const scorePct = Math.round(((pg.match_rating || 0) / 5) * 100);
  const formattingFn = (val) => {
    if (val == null) return '—';
    return Number(val).toLocaleString('en-IN');
  };

  return (
    <div className={`pg-card ${pg.Rank === 1 ? 'best-match' : ''}`}>
      <span className="card-rank">#{pg.Rank}</span>

      <div className="card-top">
        <div>
          {pg.Rank === 1 && <div className="best-badge">🔥 Best Match</div>}
          <div className="pg-name">
            PG {pg.PG_ID || pg.Rank}
            {pg.Badge && <span className="pg-badge">{pg.Badge}</span>}
          </div>
          <div className="pg-location">
            <svg width="12" height="12" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
            </svg>
            {pg.Location ? pg.Location.charAt(0).toUpperCase() + pg.Location.slice(1) : '—'}
          </div>
          <div className="stars-row">
            <div className="stars">
              {[1, 2, 3, 4, 5].map((i) => (
                <span key={i} className={`star ${i <= Math.round(pg.match_rating || 0) ? 'on' : 'off'}`}>★</span>
              ))}
            </div>
            <span className="rating-num">{pg.match_rating}/5</span>
          </div>
        </div>

        <div className="rent-pill">
          <div className="amount">₹{formattingFn(pg.Original_Rent)}</div>
          <span className="per">per month</span>
        </div>
      </div>

      <div className="card-details">
        <div className="detail-item">
          <span className="d-label">🛏 Sharing</span>
          <span className="d-val">{pg.Sharing || '—'}-person room</span>
        </div>
        <div className="detail-item">
          <span className="d-label">🍽 Meals/day</span>
          <span className="d-val">{pg.Meals_Per_Day != null ? Number(pg.Meals_Per_Day) + 2 : '—'}</span>
        </div>
        <div className="detail-item">
          <span className="d-label">🌙 Curfew</span>
          <span className="d-val">{CURFEW_MAP[pg.Curfew_Time] || '—'}</span>
        </div>
        <div className="detail-item">
          <span className="d-label">📅 Available Soon</span>
          <span className="d-val">{pg.available_soon ? '✅ Yes' : '🕐 Not yet'}</span>
        </div>
      </div>

      <div className="amenity-row">
        {AMENITIES.map((a) => (
          <span key={a.key} className={`amenity-tag ${pg[a.key] === 1 ? 'active' : ''}`}>
            {a.label}
          </span>
        ))}
      </div>

      <div className="score-bar-wrap">
        <div className="score-bar-label">
          <span>Match Score</span>
          <span>{scorePct}%</span>
        </div>
        <div className="score-bar-track">
          <div
            className="score-bar-fill"
            ref={fillRef}
            data-target={`${scorePct}%`}
            style={{ width: '0%' }}
          />
        </div>
        <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '8px', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
          <span>
            ⭐
            {pg.has_text_influence ? (
              <>
                <strong style={{ color: 'var(--accent2)', fontSize: '12px' }}>
                  {(pg.combined_display_rating || pg.average_rating || 3.5).toFixed(1)}
                </strong>
                <span style={{ color: 'var(--muted)' }}> / 5</span>
                <span style={{
                  background: 'rgba(6,214,160,0.12)',
                  border: '1px solid rgba(6,214,160,0.3)',
                  borderRadius: '999px',
                  padding: '1px 6px',
                  fontSize: '10px',
                  color: 'var(--teal)',
                  marginLeft: '4px',
                }} title={`Blends ${pg.rating_count || 0} star ratings + ${pg.review_count || 0} text reviews`}>
                  💬 combined
                </span>
                <span style={{ color: 'var(--muted)', marginLeft: '4px' }}>
                  (★ {(pg.average_rating || 3.5).toFixed(1)} · 💬 {(1.0 + (pg.avg_sentiment || 0.5) * 4.0).toFixed(1)})
                </span>
              </>
            ) : (
              <>
                {(pg.average_rating || 3.5).toFixed(1)} ({pg.rating_count || 0} ratings)
              </>
            )}
          </span>
          <span>Confidence: {(pg.Confidence_Score || 0).toFixed(2)}</span>
        </div>
      </div>

      <RatingWidget
        pgId={pg.PG_ID}
        averageRating={pg.average_rating || 3.5}
        ratingCount={pg.rating_count || 0}
      />

      <ReviewWidget
        pgId={pg.PG_ID}
        initialAvgSentiment={pg.avg_sentiment || 0.5}
        initialReviewCount={pg.review_count || 0}
        initialReviews={pg.text_reviews || []}
      />

      {pg.Why_Matched && (
        <div className="why-box">
          <strong>💡 Why recommended:</strong> {pg.Why_Matched}
        </div>
      )}
    </div>
  );
}
