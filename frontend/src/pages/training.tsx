import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PageHeader } from "@/components/dashboard/page-header"
import { TrainingsgruppenTable } from "@/components/training/trainingsgruppen-table"
import { AnwesenheitTab } from "@/components/training/anwesenheit-tab"
import { LizenzenTab } from "@/components/training/lizenzen-tab"

export function TrainingPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Training"
        description="Trainingsgruppen, Anwesenheiten und Lizenzen verwalten."
      />

      <Tabs defaultValue="gruppen">
        <TabsList>
          <TabsTrigger value="gruppen">Trainingsgruppen</TabsTrigger>
          <TabsTrigger value="anwesenheit">Anwesenheit</TabsTrigger>
          <TabsTrigger value="lizenzen">Lizenzen</TabsTrigger>
        </TabsList>
        <TabsContent value="gruppen">
          <TrainingsgruppenTable />
        </TabsContent>
        <TabsContent value="anwesenheit">
          <AnwesenheitTab />
        </TabsContent>
        <TabsContent value="lizenzen">
          <LizenzenTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
