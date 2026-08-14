import { ENTRY_TYPES, TYPE_LABELS } from '../../data/types';

const TypeFilter = ({ activeType, onChange, counts }) => {
  const handleClick = (type) => {
    onChange(activeType === type ? null : type);
  };

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by entry type">
      {ENTRY_TYPES.map((type) => {
        const isActive = activeType === type;
        const label = TYPE_LABELS[type];
        const count = counts[type];

        return (
          <button
            key={type}
            type="button"
            onClick={() => handleClick(type)}
            aria-pressed={isActive}
            className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
              isActive ? 'chip-active' : 'chip hover:bg-[var(--color-hover)] hover:text-ink'
            }`}
          >
            {label}
            {count > 0 && <span className="ml-1.5 text-subtle">{count}</span>}
          </button>
        );
      })}
    </div>
  );
};

export default TypeFilter;
