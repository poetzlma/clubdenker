import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/dashboard/page-header"
import { ProtokollList } from "@/components/dokumente/protokoll-list"
import { VorlagenList } from "@/components/dokumente/vorlagen-list"

export function DokumentePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dokumente"
        description="Protokolle, Vorlagen und Vereinsdokumente verwalten."
      />

      <Tabs defaultValue="protokolle">
        <TabsList>
          <TabsTrigger value="protokolle">Protokolle</TabsTrigger>
          <TabsTrigger value="vorlagen">Vorlagen</TabsTrigger>
        </TabsList>
        <TabsContent value="protokolle">
          <ProtokollList />
        </TabsContent>
        <TabsContent value="vorlagen">
          <VorlagenList />
        </TabsContent>
      </Tabs>
    </div>
  )
}
