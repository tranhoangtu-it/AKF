interface SectionDividerProps {
  label: string;
  id?: string;
}

export default function SectionDivider({ label, id }: SectionDividerProps) {
  return (
    <div id={id} className="relative py-2">
      <div className="max-w-5xl mx-auto px-6">
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-border-subtle to-transparent" />
          <span className="text-[11px] font-bold uppercase tracking-[0.25em] text-accent/70 whitespace-nowrap">
            {label}
          </span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-border-subtle to-transparent" />
        </div>
      </div>
    </div>
  );
}
