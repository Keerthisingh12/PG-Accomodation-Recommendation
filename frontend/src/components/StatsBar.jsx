export default function StatsBar({ results }) {
  if (!results || results.length === 0) return null;

  const avgRent = Math.round(results.reduce((sum, r) => sum + (r.Original_Rent || 0), 0) / results.length);
  const bestRating = Math.max(...results.map((r) => r.match_rating || 0));
  const formatInr = (val) => '₹' + Number(val).toLocaleString('en-IN');

  return (
    <div className="stats-bar">
      <div className="stat-chip">
        <span className="s-val">{results.length}</span>
        <span className="s-lab">Matches Found</span>
      </div>
      <div className="stat-chip">
        <span className="s-val">{formatInr(avgRent)}</span>
        <span className="s-lab">Avg Rent</span>
      </div>
      <div className="stat-chip">
        <span className="s-val">{bestRating}/5</span>
        <span className="s-lab">Best Rating</span>
      </div>
    </div>
  );
}
