import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PaymentOverview } from "@/components/finanzen/payment-overview"
import { BookingTable } from "@/components/finanzen/booking-table"
import { SepaGenerator } from "@/components/finanzen/sepa-generator"

export function FinanzenPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Finanzen</h1>
        <p className="text-muted-foreground">
          Finanzverwaltung und Buchhaltung des Vereins.
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="uebersicht">
        <TabsList>
          <TabsTrigger value="uebersicht">Übersicht</TabsTrigger>
          <TabsTrigger value="buchungen">Buchungen</TabsTrigger>
          <TabsTrigger value="sepa">SEPA</TabsTrigger>
        </TabsList>
        <TabsContent value="uebersicht">
          <PaymentOverview />
        </TabsContent>
        <TabsContent value="buchungen">
          <BookingTable />
        </TabsContent>
        <TabsContent value="sepa">
          <SepaGenerator />
        </TabsContent>
      </Tabs>
    </div>
  )
}
