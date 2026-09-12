export function Toggle({ checked, onChange, disabled, labelledBy }: {
  checked: boolean; onChange: (v: boolean) => void; disabled?: boolean; labelledBy: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={
        "relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-colors duration-200 ease-out " +
        "disabled:opacity-50 " + (checked ? "bg-accent" : "bg-line")
      }
    >
      <span
        aria-hidden
        className={
          "inline-block h-6 w-6 rounded-full bg-white shadow transition-transform duration-200 ease-out " +
          (checked ? "translate-x-7" : "translate-x-1")
        }
      />
    </button>
  );
}
