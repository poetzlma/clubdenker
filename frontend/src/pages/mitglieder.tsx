import { useState, useEffect, useCallback } from "react"
import type { Member } from "@/types/member"
import type { MemberFormData } from "@/components/mitglieder/member-form"
import { MemberTable } from "@/components/mitglieder/member-table"
import { MemberForm } from "@/components/mitglieder/member-form"
import { MemberDetail } from "@/components/mitglieder/member-detail"
import { Plus } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"

import api from "@/lib/api"

export function MitgliederPage() {
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editMember, setEditMember] = useState<Member | null>(null)
  const [detailMember, setDetailMember] = useState<Member | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const fetchMembers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ items: Member[]; total: number }>("/api/mitglieder?page_size=100")
      setMembers(data.items ?? [])
    } catch {
      setMembers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  function handleRowClick(member: Member) {
    setDetailMember(member)
    setDetailOpen(true)
  }

  function handleNewMember() {
    setEditMember(null)
    setFormOpen(true)
  }

  function handleEditFromDetail(member: Member) {
    setDetailOpen(false)
    setEditMember(member)
    setFormOpen(true)
  }

  async function handleFormSubmit(data: MemberFormData) {
    try {
      if (editMember) {
        await api.put(`/api/mitglieder/${editMember.id}`, data)
      } else {
        const created = await api.post<{ id: number }>("/api/mitglieder", data)
        if (data.abteilungen?.length && created.id) {
          for (const dept of data.abteilungen) {
            await api.post(`/api/mitglieder/${created.id}/abteilungen/${dept}`)
          }
        }
      }
    } catch {
      // ignore
    }
    await fetchMembers()
  }

  async function handleCancelMembership(member: Member) {
    try {
      await api.post(`/api/mitglieder/${member.id}/kuendigen`)
    } catch {
      // ignore
    }
    await fetchMembers()
  }

  async function handleAddDepartment(memberId: number, department: string) {
    try {
      await api.post(`/api/mitglieder/${memberId}/abteilungen/${encodeURIComponent(department)}`)
    } catch {
      // ignore
    }
    await fetchMembers()
  }

  async function handleRemoveDepartment(memberId: number, department: string) {
    try {
      await api.delete(`/api/mitglieder/${memberId}/abteilungen/${encodeURIComponent(department)}`)
    } catch {
      // ignore
    }
    await fetchMembers()
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Mitglieder"
        description="Verwalten Sie die Mitglieder Ihres Vereins."
        actions={
          <button
            onClick={handleNewMember}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Neues Mitglied
          </button>
        }
      />

      {/* Table */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">Laden...</p>
        </div>
      ) : (
        <MemberTable data={members} onRowClick={handleRowClick} />
      )}

      {/* Form Dialog */}
      <MemberForm
        open={formOpen}
        onOpenChange={setFormOpen}
        member={editMember}
        onSubmit={handleFormSubmit}
      />

      {/* Detail Dialog */}
      <MemberDetail
        open={detailOpen}
        onOpenChange={setDetailOpen}
        member={detailMember}
        onEdit={handleEditFromDetail}
        onCancel={handleCancelMembership}
        onAddDepartment={handleAddDepartment}
        onRemoveDepartment={handleRemoveDepartment}
      />
    </div>
  )
}
