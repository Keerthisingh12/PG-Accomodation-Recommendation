export default function UserSummary({ user }) {
  if (!user) return null;

  const genderLabels = ['Boys', 'Girls', 'Co-ed'];
  const gender = genderLabels[user.gender] || 'Co-ed';

  const formatInr = (val) => '₹' + Number(val).toLocaleString('en-IN');

  return (
    <div className="user-summary">
      🔍 Showing results for:
      <span>💰 <strong>{formatInr(user.budget)}</strong></span>
      {user.location && <span>📍 <strong>{user.location}</strong></span>}
      <span>👤 <strong>{gender}</strong></span>
      {user.sharing && user.sharing !== 'Any' && <span>🛏️ <strong>{user.sharing} Sharing</strong></span>}
      <span>🍽 <strong>{user.meals} meals/day</strong></span>
    </div>
  );
}
