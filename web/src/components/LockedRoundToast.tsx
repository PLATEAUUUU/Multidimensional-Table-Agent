type LockedRoundToastProps = {
  lockReason: string | null;
};

export function LockedRoundToast({ lockReason }: LockedRoundToastProps) {
  if (!lockReason) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100 shadow-frame">
      <div className="font-semibold">LockedRoundToast</div>
      <div className="mt-1 text-amber-50/90">{lockReason}</div>
    </div>
  );
}

