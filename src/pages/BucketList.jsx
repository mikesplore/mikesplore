import { bucketListItems, bucketListMeta } from '../data/bucketList';

const BucketList = () => {
  const done = bucketListItems.filter((item) => item.done);
  const remaining = bucketListItems.filter((item) => !item.done);
  const total = bucketListItems.length;
  const percent = total > 0 ? Math.round((done.length / total) * 100) : 0;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{bucketListMeta.title}</h1>
        <p className="mt-1 text-base text-muted">{bucketListMeta.description}</p>

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm text-subtle">
          <span>
            <span className="font-medium text-ink">{done.length}</span> done
          </span>
          <span>
            <span className="font-medium text-ink">{remaining.length}</span> remaining
          </span>
          <span>
            <span className="font-medium text-ink">{percent}%</span> complete
          </span>
        </div>

        <div
          className="mt-3 h-2 overflow-hidden rounded-full bg-elevated"
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${percent}% of bucket list complete`}
        >
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${percent}%` }}
          />
        </div>
      </header>

      {remaining.length > 0 && (
        <section>
          <ul className="divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
            {remaining.map((item) => (
              <li key={item.id} className="px-4 py-3.5 sm:px-5">
                <div className="flex items-start gap-3">
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full border-2 border-subtle"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-base text-ink">{item.title}</p>
                    {item.remark && (
                      <p className="mt-1 text-sm leading-relaxed text-muted">{item.remark}</p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {done.length > 0 && (
        <section>
          <h2 className="text-sm font-medium uppercase tracking-wider text-subtle">
            {done.length} completed
          </h2>
          <ul className="mt-4 divide-y divide-divider rounded-xl bg-elevated overflow-hidden">
            {done.map((item) => (
              <li key={item.id} className="px-4 py-3.5 sm:px-5">
                <div className="flex items-start gap-3">
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-base font-medium text-ink">{item.title}</p>
                    {item.remark && (
                      <p className="mt-1 text-sm leading-relaxed text-muted">{item.remark}</p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};

export default BucketList;
