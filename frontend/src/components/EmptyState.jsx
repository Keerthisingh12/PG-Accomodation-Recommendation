export default function EmptyState({ error }) {
  return (
    <div className="empty-state">
      <div className="icon">🏚️</div>
      <h3>No PGs Found</h3>
      <p>
        {error || (
          <>
            No PGs matched your filters. Try increasing your budget<br />
            or removing some amenity requirements.
          </>
        )}
      </p>
    </div>
  );
}
