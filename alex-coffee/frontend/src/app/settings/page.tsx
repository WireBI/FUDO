"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [fusoHealth, setFudoHealth] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const [status, health] = await Promise.all([api.sync.status(), api.sync.health()]);
      setSyncStatus(status);
      setFudoHealth(health.fudo_api);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        await fetchStatus();
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleSync = async () => {
    try {
      setSyncing(true);
      setError(null);
      const result = await api.sync.trigger(30);
      if (result.status === "error") {
        setError(result.error || "Sync failed");
      } else {
        await fetchStatus();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <div>
            <p className="font-semibold">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>FU.DO Connection</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">API Status</p>
              <p className="font-semibold mt-1">
                {fusoHealth === "connected" ? "Connected" : "Disconnected"}
              </p>
            </div>
            <Badge variant={fusoHealth === "connected" ? "default" : "destructive"}>
              {fusoHealth === "connected" ? (
                <CheckCircle2 className="mr-1 h-3 w-3" />
              ) : (
                <AlertCircle className="mr-1 h-3 w-3" />
              )}
              {fusoHealth || "Unknown"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data Sync</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">
              Manually trigger a sync to pull the latest data from FU.DO
            </p>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {syncing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Sync Now
                </>
              )}
            </button>
          </div>

          <div className="border-t pt-4">
            <h3 className="font-semibold text-sm mb-3">Recent Sync History</h3>
            {syncStatus?.recent_syncs && syncStatus.recent_syncs.length > 0 ? (
              <div className="space-y-2">
                {syncStatus.recent_syncs.map(
                  (sync: {
                    id: number;
                    type: string;
                    status: string;
                    records_synced: number;
                    error: string | null;
                    started_at: string;
                    completed_at: string;
                  }) => (
                    <div
                      key={sync.id}
                      className="flex items-start justify-between rounded-lg border p-3 text-sm"
                    >
                      <div className="flex-1">
                        <p className="font-medium capitalize">{sync.type}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(sync.started_at).toLocaleString()}
                        </p>
                        {sync.error && (
                          <p className="text-xs text-red-600 mt-1">{sync.error}</p>
                        )}
                      </div>
                      <div className="text-right ml-4">
                        <Badge
                          variant={sync.status === "success" ? "default" : "destructive"}
                          className="mb-1"
                        >
                          {sync.status}
                        </Badge>
                        <p className="text-xs text-muted-foreground">
                          {sync.records_synced} records
                        </p>
                      </div>
                    </div>
                  )
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No sync history yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="font-medium text-muted-foreground">Application</dt>
              <dd>Alex Coffee Analytics</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Version</dt>
              <dd>1.0.0</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Data Source</dt>
              <dd>FU.DO POS System</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
