import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PaymentOverview } from "@/components/finanzen/payment-overview"
import { InvoiceTable } from "@/components/finanzen/invoice-table"
import { BookingTable } from "@/components/finanzen/booking-table"
import { SepaGenerator } from "@/components/finanzen/sepa-generator"
import { SepaMandateTab } from "@/components/finanzen/sepa-mandate-tab"
import { KostenstellenTab } from "@/components/finanzen/kostenstellen-tab"
import { EuerReport } from "@/components/finanzen/euer-report"
import { PageHeader } from "@/components/dashboard/page-header"

export function FinanzenPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Finanzen"
        description="Finanzverwaltung und Buchhaltung des Vereins."
      />

      {/* Tabs */}
      <Tabs defaultValue="uebersicht">
        <TabsList>
          <TabsTrigger value="uebersicht">Übersicht</TabsTrigger>
          <TabsTrigger value="rechnungen">Rechnungen</TabsTrigger>
          <TabsTrigger value="buchungen">Buchungsjournal</TabsTrigger>
          <TabsTrigger value="sepa">SEPA</TabsTrigger>
          <TabsTrigger value="sepa-mandate">SEPA-Mandate</TabsTrigger>
          <TabsTrigger value="kostenstellen">Kostenstellen</TabsTrigger>
          <TabsTrigger value="euer">EÜR</TabsTrigger>
        </TabsList>
        <TabsContent value="uebersicht">
          <PaymentOverview />
        </TabsContent>
        <TabsContent value="rechnungen">
          <InvoiceTable />
        </TabsContent>
        <TabsContent value="buchungen">
          <BookingTable />
        </TabsContent>
        <TabsContent value="sepa">
          <SepaGenerator />
        </TabsContent>
        <TabsContent value="sepa-mandate">
          <SepaMandateTab />
        </TabsContent>
        <TabsContent value="kostenstellen">
          <KostenstellenTab />
        </TabsContent>
        <TabsContent value="euer">
          <EuerReport />
        </TabsContent>
      </Tabs>
    </div>
  )
}
