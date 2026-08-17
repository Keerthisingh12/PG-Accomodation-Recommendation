import { useState, useRef, useCallback } from 'react';
import api from '../api';

/* ── Client-side sentiment preview (mirrors server logic) ── */
const POS_WORDS = [
  'excellent','great','good','nice','amazing','awesome','fantastic',
  'superb','wonderful','perfect','love','happy','satisfied','clean','comfortable',
  'spacious','helpful','friendly','tasty','delicious','affordable','value',
  'safe','secure','quiet','peaceful','decent','recommended','recommend',
  'brilliant','impressive','reasonable','convenient','accessible',
  'like','enjoy','enjoyed','works','working','fast','quick','smooth',
  'warm','cozy','neat','maintained','maintained well',
];
const NEG_WORDS = [
  'terrible','horrible','awful','bad','worst','dirty','noisy','rude',
  'unhelpful','overpriced','expensive','broken','slow','poor','disgusting','filthy',
  'avoid','scam','fraud','cheating','disappointed','pathetic','unhygienic','unsafe',
  'stale','tasteless','cockroaches','pests','waste','problem','problems',
  'issue','issues','properly','complaint','complaints',
];
const AMPLIFIERS = new Set(['very','really','extremely','super','absolutely','highly','totally','so']);
const NEGATORS = new Set(['not','no','never',"didn't",'dont','don\'t','does not','doesn\'t','isn\'t','is not','wasn\'t', 'was not','won\'t','will not','can\'t','cannot','did not']);

function localSentimentScore(text) {
  const cleaned = text.toLowerCase().replace(/[^a-z0-9'\s]/g, ' ').replace(/\s+/g, ' ').trim();
  const words = cleaned.split(' ');
  let raw = 0;
  let mod = 1;
  let modDecay = 0;

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const bigram = i + 1 < words.length ? w + ' ' + words[i + 1] : '';
    if (NEGATORS.has(bigram)) { mod *= -1; modDecay = 0; i++; continue; }
    if (NEGATORS.has(w)) { mod *= -1; modDecay = 0; continue; }
    if (AMPLIFIERS.has(w)) { mod *= 1.4; modDecay = 0; continue; }
    if (POS_WORDS.includes(w)) { raw += 1.0 * mod; mod = 1; modDecay = 0; }
    else if (NEG_WORDS.includes(w)) { raw += -1.0 * mod; mod = 1; modDecay = 0; }
    else { if (mod !== 1) { modDecay++; if (modDecay >= 3) { mod = 1; modDecay = 0; } } }
  }

  const clip = 8;
  return Math.max(0, Math.min(1, (Math.max(-clip, Math.min(clip, raw)) + clip) / (2 * clip)));
}

function scoreToMeta(score) {
  if (score >= 0.70) return { label: 'Excellent', cls: 'excellent', emoji: '🌟' };
  if (score >= 0.50) return { label: 'Good', cls: 'good', emoji: '👍' };
  if (score >= 0.30) return { label: 'Average', cls: 'average', emoji: '😐' };
  return { label: 'Poor', cls: 'poor', emoji: '👎' };
}

function reviewSentimentClass(score) {
  if (score >= 0.7) return 'excellent';
  if (score >= 0.5) return 'good';
  if (score >= 0.3) return 'average';
  return 'poor';
}

function reviewSentimentLabel(score) {
  if (score >= 0.9) return 'Excellent';
  if (score >= 0.6) return 'Good';
  if (score >= 0.4) return 'Average';
  return 'Poor';
}

export default function ReviewWidget({ pgId, initialAvgSentiment, initialReviewCount, initialReviews }) {
  const [open, setOpen] = useState(false);
  const [reviewText, setReviewText] = useState('');
  const [preview, setPreview] = useState(null);
  const [toast, setToast] = useState('');
  const [toastError, setToastError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reviews, setReviews] = useState(initialReviews || []);
  const [avgSentiment, setAvgSentiment] = useState(initialAvgSentiment || 0.5);
  const [reviewCount, setReviewCount] = useState(initialReviewCount || 0);
  const debounceRef = useRef(null);

  const handleToggle = () => setOpen((prev) => !prev);

  const handleTextChange = useCallback((e) => {
    const val = e.target.value;
    setReviewText(val);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!val.trim()) {
      setPreview(null);
      return;
    }
    debounceRef.current = setTimeout(() => {
      const score = localSentimentScore(val);
      const meta = scoreToMeta(score);
      setPreview({ score, ...meta });
    }, 350);
  }, []);

  const handleSubmit = async () => {
    const text = reviewText.trim();
    if (!text) {
      setToast('Please write a review first!');
      setToastError(true);
      return;
    }
    if (text.length < 5) {
      setToast('Review is too short (minimum 5 characters).');
      setToastError(true);
      return;
    }

    setSubmitting(true);
    setToast('');
    try {
      const { data } = await api.post('/submit-review', { pg_id: pgId, review_text: text });
      if (data.success) {
        setToast(`${scoreToMeta(data.sentiment_score).emoji} Saved! Sentiment: ${data.sentiment_label} (score ${data.sentiment_score.toFixed(2)})`);
        setToastError(false);
        setReviewText('');
        setPreview(null);
        setReviewCount(data.review_count);
        setAvgSentiment(data.avg_sentiment);
        setReviews(data.reviews || []);
      }
    } catch {
      setToast('Network error. Please try again.');
      setToastError(true);
    } finally {
      setSubmitting(false);
    }
  };

  const avgCls = avgSentiment >= 0.7 ? 'excellent' : avgSentiment >= 0.5 ? 'good' : avgSentiment >= 0.3 ? 'average' : 'poor';
  const avgPct = (avgSentiment * 100).toFixed(0);

  return (
    <div className="review-widget">
      <div className="review-widget-header" onClick={handleToggle}>
        <span className="review-widget-title">
          💬 Write a Review
          <span className="review-badge-count">
            {reviewCount > 0 ? `${reviewCount} review${reviewCount !== 1 ? 's' : ''}` : 'Be the first!'}
          </span>
        </span>
        <span className={`review-widget-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>

      <div className={`review-widget-body ${open ? 'open' : ''}`}>
        {/* Avg sentiment bar */}
        <div className="avg-sentiment-bar" style={reviewCount === 0 ? { display: 'none' } : {}}>
          <span className="avg-sent-label">Review Sentiment</span>
          <div className="avg-sent-track">
            <div className={`avg-sent-fill ${avgCls}`} style={{ width: `${avgPct}%` }} />
          </div>
          <span className="sent-label">{avgCls.charAt(0).toUpperCase() + avgCls.slice(1)}</span>
        </div>

        {/* Past reviews */}
        <div className="past-reviews">
          {reviews.length > 0
            ? reviews.map((rev, i) => {
                const cls = reviewSentimentClass(rev.sentiment_score);
                const lbl = reviewSentimentLabel(rev.sentiment_score);
                return (
                  <div className="past-review-item" key={i}>
                    <div className="past-review-text">&ldquo;{rev.text}&rdquo;</div>
                    <div className="past-review-meta">
                      <span className={`sent-dot ${cls}`} />
                      <span className="sent-label">{lbl}</span>
                      <span className="sent-score">{rev.sentiment_score.toFixed(2)} / 1.0</span>
                    </div>
                  </div>
                );
              })
            : <div className="no-reviews-msg">No reviews yet — be the first to share your experience!</div>
          }
        </div>

        {/* Input area */}
        <textarea
          className="review-textarea"
          placeholder="e.g. Great location, food is decent, WiFi is fast. Overall a good place to stay!"
          maxLength={500}
          value={reviewText}
          onChange={handleTextChange}
        />
        {preview && (
          <div className={`sentiment-indicator visible ${preview.cls}`}>
            {preview.emoji} Preview: {preview.label} ({preview.score.toFixed(2)})
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Max 500 characters</span>
          <button
            className="submit-review-btn"
            onClick={handleSubmit}
            disabled={submitting}
          >
            📨 {submitting ? '…' : 'Submit Review'}
          </button>
        </div>
        <div className={`review-toast ${toastError ? 'error' : ''}`}>{toast}</div>
      </div>
    </div>
  );
}
