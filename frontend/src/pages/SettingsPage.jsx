import { useEffect, useState } from "react";
import { GitBranch, HardDrive, Link2, Network, Shapes } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authGet } from "@/lib/api";
import { toast } from "sonner";


export default function SettingsPage() {
  const [driveStatus, setDriveStatus] = useState(null);
  const [blueprint, setBlueprint] = useState(null);
  const [connecting, setConnecting] = useState(false);

  const loadSettings = async () => {
    const [driveResponse, blueprintResponse] = await Promise.all([
      authGet("/integrations/drive/status"),
      authGet("/system/blueprint"),
    ]);
    setDriveStatus(driveResponse);
    setBlueprint(blueprintResponse);
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const connectDrive = async () => {
    setConnecting(true);
    try {
      const response = await authGet("/integrations/drive/connect");
      window.open(response.authorization_url, "_blank", "noopener,noreferrer");
      toast.success("Google Drive connection window opened.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Google Drive connection is not configured yet");
    } finally {
      setConnecting(false);
    }
  };

  if (!driveStatus || !blueprint) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="settings-loading-state">Loading settings...</div>;
  }

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="settings-drive-card">
          <CardContent className="p-8">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Google Drive sync</p>
                <h2 className="mt-2 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Structured mirror for photos and review JSON</h2>
              </div>
              <HardDrive className="h-6 w-6 text-[#243e36]" />
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Badge className="border-0 bg-[#edf0e7] px-3 py-1 text-[#243e36]" data-testid="settings-drive-configured-badge">Configured: {driveStatus.configured ? "Yes" : "No"}</Badge>
              <Badge className="border-0 bg-[#edf0e7] px-3 py-1 text-[#243e36]" data-testid="settings-drive-connected-badge">Connected: {driveStatus.connected ? "Yes" : "No"}</Badge>
            </div>

            <div className="mt-6 rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid="settings-drive-path-card">
              <p className="text-sm font-semibold text-[#243e36]">Drive folder structure</p>
              <p className="mt-2 text-sm text-[#5c6d64]" data-testid="settings-drive-folder-structure">/QA/{'{Year}'}/{'{Division}'}/{'{ServiceType}'}/{'{JobID}'}_{'{SubmissionID}'}/</p>
              <p className="mt-4 text-sm text-[#5c6d64]">Required env values: {driveStatus.required_env.join(", ")}</p>
            </div>

            <Button onClick={connectDrive} disabled={connecting} className="mt-6 h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="settings-drive-connect-button"><Link2 className="mr-2 h-4 w-4" />{connecting ? "Opening connection..." : "Connect Google Drive"}</Button>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="settings-tech-stack-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Suggested stack</p>
            <h2 className="mt-2 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight">Implementation blueprint</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {[
                { icon: Shapes, label: "Frontend", value: blueprint.suggested_stack.frontend },
                { icon: Network, label: "Backend", value: blueprint.suggested_stack.backend },
                { icon: GitBranch, label: "Database", value: blueprint.suggested_stack.database },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="rounded-[28px] border border-white/10 bg-white/10 p-5" data-testid={`settings-stack-card-${item.label.toLowerCase()}`}>
                    <Icon className="h-5 w-5 text-[#d8f3dc]" />
                    <p className="mt-4 text-sm text-white/70">{item.label}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{item.value}</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="settings-architecture-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Application architecture</p>
            <div className="mt-5 space-y-5">
              {Object.entries(blueprint.architecture).map(([key, items]) => (
                <div key={key} data-testid={`settings-architecture-section-${key}`}>
                  <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815]">{key}</h3>
                  <ul className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                    {items.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="settings-schema-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Schema, screens, workflow</p>
            <div className="mt-5 grid gap-5">
              <div data-testid="settings-schema-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815]">Collections</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {blueprint.database_schema.map((item) => <Badge key={item} className="border-0 bg-[#edf0e7] px-3 py-1 text-[#243e36]">{item}</Badge>)}
                </div>
              </div>
              <div data-testid="settings-ui-screen-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815]">UI screens</h3>
                <ul className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                  {blueprint.ui_screens.map((item) => <li key={item}>• {item}</li>)}
                </ul>
              </div>
              <div data-testid="settings-workflow-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815]">Workflow diagram</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {blueprint.workflow_diagram.map((item, index) => <Badge key={item} className="border-0 bg-[#243e36] px-3 py-1 text-white">{index + 1}. {item}</Badge>)}
                </div>
              </div>
              <div data-testid="settings-plan-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815]">Implementation plan</h3>
                <ul className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                  {blueprint.implementation_plan.map((item) => <li key={item}>• {item}</li>)}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="settings-learning-roadmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Learning roadmap</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">How this system can grow into automated quality checks</h3>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {[
              'Phase 1: humans review photo batches and store rubric labels, comments, and variance data.',
              'Phase 2: AI suggests likely scores and issues from the labeled image archive.',
              'Phase 3: AI handles most grading while humans supervise edge cases and drift.',
            ].map((step, index) => (
              <div key={step} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4 text-sm text-[#5c6d64]" data-testid={`settings-learning-roadmap-step-${index + 1}`}>{step}</div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}