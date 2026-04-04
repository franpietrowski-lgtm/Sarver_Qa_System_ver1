import { Card, CardContent } from "@/components/ui/card";


export default function StatCard({ icon: Icon, label, value, hint, testId }) {
  return (
    <Card className="h-full rounded-[28px] border-border/80 bg-[var(--card)] shadow-sm" data-testid={testId}>
      <CardContent className="flex h-full items-start justify-between gap-4 p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-[var(--muted-foreground)]" data-testid={`${testId}-label`}>{label}</p>
          <p className="mt-4 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[var(--foreground)]" data-testid={`${testId}-value`}>{value}</p>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]" data-testid={`${testId}-hint`}>{hint}</p>
        </div>
        <div className="rounded-2xl bg-[var(--accent)] p-3 text-[var(--foreground)]">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
