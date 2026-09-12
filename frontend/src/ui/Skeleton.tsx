// Skeletons match the final layout; one soft pulse, nothing fancier (brief §11).
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulseSoft rounded-xl bg-sand ${className}`} />;
}
export function CardSkeleton({ lines = 2 }: { lines?: number }) {
  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-line bg-card p-4">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={i === 0 ? "h-6 w-3/4" : "h-4 w-1/2"} />
      ))}
    </div>
  );
}
