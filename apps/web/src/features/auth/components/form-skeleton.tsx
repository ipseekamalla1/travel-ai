/** Placeholder matching the auth form's layout while search params resolve. */
export function AuthFormSkeleton({ fields }: { fields: number }) {
  return (
    <div aria-hidden="true" className="grid animate-pulse gap-5">
      {Array.from({ length: fields }, (_, i) => (
        <div key={i} className="grid gap-1.5">
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="h-11 rounded-lg bg-muted" />
        </div>
      ))}
      <div className="h-11 rounded-full bg-muted" />
    </div>
  );
}
