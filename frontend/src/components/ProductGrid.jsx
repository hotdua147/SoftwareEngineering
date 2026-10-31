import ProductCard from './ProductCard.jsx';

export default function ProductGrid({ rows, emptyText }) {
  return (
    <div className="grid" aria-live="polite">
      {rows.length
        ? rows.map((r, i) => <ProductCard key={r.item.sku} item={r.item} rank={r.rank ?? i + 1} score={r.score} />)
        : <p className="empty">{emptyText}</p>}
    </div>
  );
}
