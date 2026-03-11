import { useState } from "react"
import { Copy, Check, ExternalLink } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"

const MCP_URL = "https://klubdenker.poetzl.org/mcp/"

function CopyBlock({ code, language = "json" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group relative">
      <pre className="overflow-x-auto rounded-lg border bg-muted p-4 text-sm">
        <code className={`language-${language}`}>{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={handleCopy}
      >
        {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  )
}

function StepNumber({ n }: { n: number }) {
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
      {n}
    </span>
  )
}

const claudeDesktopConfig = `{
  "mcpServers": {
    "klubdenker": {
      "url": "${MCP_URL}"
    }
  }
}`

const claudeCodeConfig = `{
  "mcpServers": {
    "klubdenker": {
      "url": "${MCP_URL}"
    }
  }
}`

const cursorConfig = `{
  "mcpServers": {
    "klubdenker": {
      "url": "${MCP_URL}"
    }
  }
}`

const windmillConfig = `{
  "mcpServers": {
    "klubdenker": {
      "url": "${MCP_URL}"
    }
  }
}`

const exampleTools = [
  { name: "mitglieder_suchen", desc: "Mitglieder suchen und filtern" },
  { name: "mitglied_anlegen", desc: "Neues Mitglied anlegen" },
  { name: "mitglied_details", desc: "Details zu einem Mitglied abrufen" },
  { name: "buchung_anlegen", desc: "Neue Buchung erfassen" },
  { name: "finanzbericht_erstellen", desc: "Finanzbericht generieren" },
  { name: "beitragseinzug_starten", desc: "Beitragseinzug durchführen" },
  { name: "sepa_xml_generieren", desc: "SEPA-Lastschrift XML erstellen" },
  { name: "dashboard_vorstand", desc: "Vorstand-Dashboard abrufen" },
  { name: "dashboard_schatzmeister", desc: "Schatzmeister-Dashboard" },
  { name: "training_verwalten", desc: "Trainingsgruppen verwalten" },
  { name: "mahnlauf_starten", desc: "Mahnlauf durchführen" },
  { name: "rechnung_erstellen", desc: "Rechnung erstellen" },
]

export function McpSetupPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="MCP-Server Einrichtung"
        description="Verbinden Sie Ihren KI-Assistenten mit Klubdenker."
      />

      {/* Intro */}
      <Card>
        <CardHeader>
          <CardTitle>Was ist MCP?</CardTitle>
          <CardDescription>
            Model Context Protocol -- der offene Standard für KI-Integrationen
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            MCP (Model Context Protocol) ist ein offener Standard von Anthropic, der es
            KI-Assistenten ermöglicht, direkt mit externen Systemen zu kommunizieren.
            Mit der Klubdenker MCP-Anbindung kann Ihr KI-Assistent:
          </p>
          <ul className="ml-4 list-disc space-y-1">
            <li>Mitglieder suchen, anlegen und verwalten</li>
            <li>Buchungen und Rechnungen erstellen</li>
            <li>SEPA-Lastschriften generieren</li>
            <li>Finanzberichte und Dashboards abrufen</li>
            <li>Beiträge berechnen und Mahnläufe durchführen</li>
            <li>Trainingsgruppen und Anwesenheiten verwalten</li>
          </ul>
          <p>
            Server-URL: <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{MCP_URL}</code>
          </p>
        </CardContent>
      </Card>

      {/* Setup per Client */}
      <Tabs defaultValue="claude-desktop">
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="claude-desktop">Claude Desktop</TabsTrigger>
          <TabsTrigger value="claude-code">Claude Code (CLI)</TabsTrigger>
          <TabsTrigger value="cursor">Cursor</TabsTrigger>
          <TabsTrigger value="other">Andere Clients</TabsTrigger>
        </TabsList>

        {/* Claude Desktop */}
        <TabsContent value="claude-desktop" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Claude Desktop</CardTitle>
              <CardDescription>Anthropics Desktop-App für Claude</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-start gap-3">
                <StepNumber n={1} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Konfigurationsdatei öffnen</p>
                  <p className="text-sm text-muted-foreground">
                    Öffnen Sie Claude Desktop und gehen Sie zu{" "}
                    <strong>Einstellungen &rarr; Entwickler &rarr; Konfiguration bearbeiten</strong>.
                    Alternativ die Datei direkt bearbeiten:
                  </p>
                  <CopyBlock
                    language="text"
                    code={`macOS: ~/Library/Application Support/Claude/claude_desktop_config.json\nWindows: %APPDATA%\\Claude\\claude_desktop_config.json`}
                  />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={2} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Klubdenker-Server hinzufügen</p>
                  <p className="text-sm text-muted-foreground">
                    Fügen Sie folgende Konfiguration ein (oder ergänzen Sie den bestehenden <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">mcpServers</code>-Block):
                  </p>
                  <CopyBlock code={claudeDesktopConfig} />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={3} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Claude Desktop neu starten</p>
                  <p className="text-sm text-muted-foreground">
                    Nach dem Speichern der Konfiguration Claude Desktop neu starten.
                    Im Chat sollte nun ein Hammer-Symbol erscheinen, das die verfügbaren Tools anzeigt.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Claude Code */}
        <TabsContent value="claude-code" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Claude Code (CLI)</CardTitle>
              <CardDescription>Anthropics CLI-Tool für Entwickler</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-start gap-3">
                <StepNumber n={1} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Projekt-Konfiguration anlegen</p>
                  <p className="text-sm text-muted-foreground">
                    Erstellen Sie eine <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">.mcp.json</code> Datei
                    im Projektverzeichnis:
                  </p>
                  <CopyBlock code={claudeCodeConfig} />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={2} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Oder per CLI hinzufügen</p>
                  <CopyBlock
                    language="bash"
                    code={`claude mcp add klubdenker --transport http ${MCP_URL}`}
                  />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={3} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Testen</p>
                  <p className="text-sm text-muted-foreground">
                    Starten Sie Claude Code und fragen Sie z.B.:{" "}
                    <em>&quot;Zeige mir alle aktiven Mitglieder&quot;</em>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cursor */}
        <TabsContent value="cursor" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Cursor</CardTitle>
              <CardDescription>KI-gestützter Code-Editor</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-start gap-3">
                <StepNumber n={1} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">MCP-Einstellungen öffnen</p>
                  <p className="text-sm text-muted-foreground">
                    Gehen Sie zu <strong>Cursor Settings &rarr; MCP</strong> und klicken Sie auf{" "}
                    <strong>&quot;Add new global MCP server&quot;</strong>.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={2} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Konfiguration einfügen</p>
                  <CopyBlock code={cursorConfig} />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={3} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Verbindung prüfen</p>
                  <p className="text-sm text-muted-foreground">
                    Nach dem Speichern sollte der Server in den MCP-Einstellungen als verbunden angezeigt werden.
                    Im Composer (Agent-Modus) stehen die Tools dann zur Verfügung.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Other */}
        <TabsContent value="other" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Andere MCP-Clients</CardTitle>
              <CardDescription>Allgemeine Einrichtung für beliebige MCP-kompatible Clients</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-start gap-3">
                <StepNumber n={1} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Verbindungsdaten</p>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p><strong>Transport:</strong> Streamable HTTP</p>
                    <p><strong>URL:</strong></p>
                    <CopyBlock language="text" code={MCP_URL} />
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={2} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">Standard MCP-Konfiguration</p>
                  <p className="text-sm text-muted-foreground">
                    Die meisten Clients verwenden dieses Format:
                  </p>
                  <CopyBlock code={windmillConfig} />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <StepNumber n={3} />
                <div className="space-y-2 flex-1">
                  <p className="text-sm font-medium">MCP Inspector</p>
                  <p className="text-sm text-muted-foreground">
                    Zum Testen und Debuggen können Sie den offiziellen MCP Inspector verwenden:
                  </p>
                  <CopyBlock language="bash" code={`npx @modelcontextprotocol/inspector`} />
                  <p className="text-sm text-muted-foreground">
                    Wählen Sie <strong>Streamable HTTP</strong> als Transport und geben Sie die URL ein.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Available Tools */}
      <Card>
        <CardHeader>
          <CardTitle>Verfügbare Tools</CardTitle>
          <CardDescription>
            Diese Funktionen stehen Ihrem KI-Assistenten nach der Einrichtung zur Verfügung.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {exampleTools.map((tool) => (
              <div
                key={tool.name}
                className="flex flex-col rounded-lg border p-3"
              >
                <code className="text-xs font-semibold text-primary">{tool.name}</code>
                <span className="mt-1 text-xs text-muted-foreground">{tool.desc}</span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Insgesamt 40+ Tools verfügbar. Der KI-Assistent wählt automatisch das passende Tool basierend auf Ihrer Anfrage.
          </p>
        </CardContent>
      </Card>

      {/* Example Prompts */}
      <Card>
        <CardHeader>
          <CardTitle>Beispiel-Anfragen</CardTitle>
          <CardDescription>So können Sie mit Ihrem KI-Assistenten arbeiten:</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              "Zeige mir alle Mitglieder der Fussball-Abteilung.",
              "Lege ein neues Mitglied an: Max Mustermann, geboren am 15.03.1990, Kategorie Erwachsene.",
              "Wie ist der aktuelle Kassenstand aufgeteilt nach Sphären?",
              "Erstelle eine SEPA-Lastschrift für die Beiträge im März.",
              "Welche Mitglieder haben offene Rechnungen?",
              "Starte einen Mahnlauf für überfällige Beiträge.",
            ].map((prompt) => (
              <div
                key={prompt}
                className="rounded-lg border bg-muted/50 px-4 py-3 text-sm italic text-muted-foreground"
              >
                &quot;{prompt}&quot;
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Links */}
      <div className="flex flex-wrap gap-3 text-sm">
        <a
          href="https://modelcontextprotocol.io"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
        >
          MCP Dokumentation <ExternalLink className="h-3 w-3" />
        </a>
        <a
          href="https://claude.ai/download"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
        >
          Claude Desktop herunterladen <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  )
}
