"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, AlertCircle, CheckCircle2, Eye, EyeOff, Copy } from "lucide-react";

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [credentialStatus, setCredentialStatus] = useState<any>(null);
  const [currentCredential, setCurrentCredential] = useState<any>(null);

  const [newId, setNewId] = useState("");
  const [newSecret, setNewSecret] = useState("");
  const [updateLoading, setUpdateLoading] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  const handleAuthenticate = async () => {
    try {
      setLoading(true);
      setError(null);
      const [cred, status] = await Promise.all([
        api.admin.getCredentials(adminKey),
        api.admin.checkStatus(adminKey),
      ]);
      setCurrentCredential(cred);
      setCredentialStatus(status);
      setAuthenticated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSecret = async () => {
    if (!newSecret.trim()) {
      setError("Secret cannot be empty");
      return;
    }

    try {
      setUpdateLoading(true);
      setError(null);
      await api.admin.updateCredentials(adminKey, newSecret, newId);
      setUpdateSuccess(true);
      setNewSecret("");
      setNewId("");
      setTimeout(() => setUpdateSuccess(false), 3000);
      // Refresh credential display
      const [cred, status] = await Promise.all([
        api.admin.getCredentials(adminKey),
        api.admin.checkStatus(adminKey),
      ]);
      setCurrentCredential(cred);
      setCredentialStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setUpdateLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <div className="space-y-8">
        <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>

        <Card>
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Enter your admin API key to access the credentials management
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Admin API Key</label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showKey ? "text" : "password"}
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    placeholder="Enter your admin API key"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    onKeyPress={(e) => e.key === "Enter" && handleAuthenticate()}
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <button
                  onClick={handleAuthenticate}
                  disabled={loading || !adminKey.trim()}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    "Authenticate"
                  )}
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>About Admin Access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              The admin API key is stored in your Railway environment variables as <code className="bg-muted px-1.5 py-0.5 rounded">ADMIN_API_KEY</code>
            </p>
            <p>
              This key protects access to FU.DO API credential management. Keep it secure and never share it.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
        <button
          onClick={() => {
            setAuthenticated(false);
            setAdminKey("");
            setNewSecret("");
            setError(null);
          }}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Sign out
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {updateSuccess && (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">API credentials updated successfully!</p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Credentials Status</CardTitle>
          <CardDescription>Current FU.DO API credential configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {credentialStatus && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Status</p>
                  <div className="flex items-center gap-2">
                    <Badge variant={credentialStatus.configured ? "default" : "destructive"}>
                      {credentialStatus.configured ? "Configured" : "Not Configured"}
                    </Badge>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Source</p>
                  <Badge variant="outline">{credentialStatus.source}</Badge>
                </div>
              </div>

              <div className="border-t pt-4">
                <p className="text-sm text-muted-foreground">{credentialStatus.note}</p>
              </div>

              {credentialStatus.source === "database" && credentialStatus.updated_at && (
                <div className="border-t pt-4 space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Last updated: {new Date(credentialStatus.updated_at).toLocaleString()}
                  </p>
                  {credentialStatus.updated_by && (
                    <p className="text-xs text-muted-foreground">
                      Updated by: {credentialStatus.updated_by}
                    </p>
                  )}
                </div>
              )}

              {currentCredential && (
                <div className="border-t pt-4 space-y-4">
                  {currentCredential.fudo_api_id && (
                    <div>
                      <p className="text-sm font-medium mb-2">Current API ID</p>
                      <div className="flex items-center gap-2 font-mono text-sm bg-muted p-2 rounded">
                        {currentCredential.fudo_api_id}
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(currentCredential.fudo_api_id);
                          }}
                          className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium mb-2">Current Secret (masked)</p>
                    <div className="flex items-center gap-2 font-mono text-sm bg-muted p-2 rounded">
                      {currentCredential.fudo_api_secret_masked}
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(currentCredential.fudo_api_secret_masked);
                        }}
                        className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Update FU.DO API Secret</CardTitle>
          <CardDescription>
            Replace your FU.DO API secret (safely encrypted and stored in database)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">API ID</label>
              <input
                type="text"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                placeholder="Enter your FU.DO API ID"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">API Secret</label>
              <input
                type="password"
                value={newSecret}
                onChange={(e) => setNewSecret(e.target.value)}
                placeholder="Paste your FU.DO API secret"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <p className="text-xs text-muted-foreground">
                Generate these in FU.DO Admin &gt; Users &gt; Establecer API Secret
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleUpdateSecret}
              disabled={updateLoading || !newSecret.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {updateLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update Secret"
              )}
            </button>
            {(newSecret || newId) && (
              <button
                onClick={() => {
                  setNewSecret("");
                  setNewId("");
                }}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800 border border-blue-200">
            <p className="font-medium mb-1">How it works:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Your secret is encrypted with a Fernet key before storage</li>
              <li>Only the encrypted version is stored in the database</li>
              <li>The app decrypts it on-demand for API calls</li>
              <li>Never displayed in plain text (only masked last 4 chars)</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
