import { Card, CardContent } from "@/components/ui/card";


export default function StatCard({ icon: Icon, label, value, hint, testId }) {
  return (
    <Card className="h-full rounded-[28px] border-border/80 bg-white/90 shadow-sm" data-testid={testId}>
      <CardContent className="flex h-full items-start justify-between gap-4 p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-[#5f7464]" data-testid={`${testId}-label`}>{label}</p>
          <p className="mt-4 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]" data-testid={`${testId}-value`}>{value}</p>
          <p className="mt-2 text-sm text-[#5c6d64]" data-testid={`${testId}-hint`}>{hint}</p>
        </div>
        <div className="rounded-2xl bg-[#edf0e7] p-3 text-[#243e36]">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}