import { useEffect, useState } from "react";
import { Download, FileJson, FileSpreadsheet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authGet, authPost, getApiOrigin } from "@/lib/api";
import { toast } from "sonner";


export default function ExportsPage() {
  const [exportsList, setExportsList] = useState([]);
  const [running, setRunning] = useState("");

  const loadExports = async () => {
    const response = await authGet("/exports");
    setExportsList(response);
  };

  useEffect(() => {
    loadExports();
  }, []);

  const runExport = async (datasetType, exportFormat) => {
    const key = `${datasetType}-${exportFormat}`;
    setRunning(key);
    try {
      await authPost("/exports/run", { dataset_type: datasetType, export_format: exportFormat });
      toast.success(`${datasetType} export created in ${exportFormat.toUpperCase()}.`);
      await loadExports();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Export failed");
    } finally {
      setRunning("");
    }
  };

  const apiOrigin = getApiOrigin();

  return (
    <div className="space-y-6" data-testid="exports-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="exports-hero-card">
        <CardContent className="grid gap-6 p-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Dataset export system</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Package review history into AI-ready JSONL or analyst-friendly CSV.</h2>
            <p className="mt-4 text-sm leading-6 text-[#5c6d64]">Full Dataset includes every review layer. Owner Gold includes only owner-approved calibration records.</p>
          </div>
          <div className="grid gap-3 rounded-[28px] border border-border bg-[#edf0e7] p-5">
            <Button onClick={() => runExport("full", "jsonl")} disabled={running === "full-jsonl"} className="h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="export-full-jsonl-button"><FileJson className="mr-2 h-4 w-4" />{running === "full-jsonl" ? "Building export..." : "Full Dataset · JSONL"}</Button>
            <Button onClick={() => runExport("full", "csv")} disabled={running === "full-csv"} className="h-12 rounded-2xl bg-white text-[#243e36] hover:bg-[#f6f6f2]" data-testid="export-full-csv-button"><FileSpreadsheet className="mr-2 h-4 w-4" />{running === "full-csv" ? "Building export..." : "Full Dataset · CSV"}</Button>
            <Button onClick={() => runExport("owner_gold", "jsonl")} disabled={running === "owner_gold-jsonl"} className="h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="export-owner-jsonl-button"><FileJson className="mr-2 h-4 w-4" />{running === "owner_gold-jsonl" ? "Building export..." : "Owner Gold · JSONL"}</Button>
            <Button onClick={() => runExport("owner_gold", "csv")} disabled={running === "owner_gold-csv"} className="h-12 rounded-2xl bg-white text-[#243e36] hover:bg-[#f6f6f2]" data-testid="export-owner-csv-button"><FileSpreadsheet className="mr-2 h-4 w-4" />{running === "owner_gold-csv" ? "Building export..." : "Owner Gold · CSV"}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="exports-history-card">
        <CardContent className="p-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Recent exports</p>
              <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Download history</h3>
            </div>
            <Badge className="border-0 bg-[#edf0e7] px-3 py-1 text-[#243e36]" data-testid="exports-count-badge">{exportsList.length} exports</Badge>
          </div>

          <div className="mt-6 space-y-3">
            {exportsList.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-[26px] border border-border bg-[#f6f6f2] p-4" data-testid={`exports-row-${item.id}`}>
                <div>
                  <p className="text-sm font-semibold text-[#243e36]" data-testid={`exports-row-title-${item.id}`}>{item.dataset_type} · {item.export_format.toUpperCase()}</p>
                  <p className="mt-1 text-sm text-[#5c6d64]" data-testid={`exports-row-meta-${item.id}`}>{item.row_count} rows · {item.created_at.slice(0, 19).replace("T", " ")}</p>
                </div>
                <Button type="button" onClick={() => window.open(`${apiOrigin}/api/exports/${item.id}/download`, "_blank", "noopener,noreferrer")} className="h-11 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`exports-download-button-${item.id}`}><Download className="mr-2 h-4 w-4" />Download</Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}