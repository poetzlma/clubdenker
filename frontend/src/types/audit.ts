export interface AuditLogEntry {
  id: number
  user_id: number | null
  action: string
  entity_type: string
  entity_id: number | null
  details: string | null
  ip_address: string | null
  created_at: string
}
